#!/usr/bin/env python3
"""Render a long-form plan (composition LongEdit) in a fraction of the time, to a YouTube-sized file.

    python3 fast_render.py edits/NAME [--frames A-B] [--bitrate 12M]   -> edits/NAME/render.mp4
    python3 fast_render.py demo

Remotion draws every frame as a web page: about 3.5 s of rendering per second of a 1080p long-form cut on the
Mac (cold-calling-one: 80 min for 23 min). But about three quarters of a long-form edit is the speaker alone,
the cut's own footage with at most a hard punch-in zoom: that needs no page at all. So:
  - the plain stretches are cut from the render-size copy of the cut with ffmpeg (the zoom as a crop about the
    head, exactly as LongEdit's Footage scales: origin at the head's centre and top), on the Mac's hardware
    encoder;
  - only the stretches with a graphic (any kind, overlays included) go through Remotion (render.mjs ranges),
    bundled once, video only;
  - the sound is mixed once for the whole edit with ffmpeg (the voice track, the music bed, the sound cues: the
    same files and levels the plan gives LongEdit);
  - everything is joined and encoded once, at a bitrate YouTube recommends for 1080p (12 Mbit/s; Remotion's
    default x264 quality ran ~50 Mbit/s, 8-9 GB for 23 min, which YouTube re-encodes anyway).
Frames in == frames out is checked at the end.
"""
import argparse
import concurrent.futures as cf
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MERGE_GAP_S = 1.0       # graphic stretches closer than this are rendered as one (no 1-frame plain slivers)
BITRATE = "12M"         # final video bitrate at 1080p (YouTube's recommendation is 8 for 1080p30 SDR)
OVERLAYS = ("label", "buttons", "lower", "phrase")


def frame_of(t, fps):
    """The first frame LongEdit shows at or after time t (it tests t >= start with t = frame / fps)."""
    return math.ceil(t * fps - 1e-6)


def stretches(plan, lo=0, hi=None):
    """[(a, b, kind)] covering frames lo..hi-1: kind "gfx" (Remotion) or "plain" (ffmpeg), in order."""
    fps, n = plan["fps"], plan["durationInFrames"]
    hi = n if hi is None else hi
    gap = round(MERGE_GAP_S * fps)
    g = sorted((max(lo, frame_of(x["start"], fps)), min(hi, frame_of(x["end"], fps))) for x in plan["graphics"])
    merged = []
    for a, b in g:
        if b <= a:
            continue
        if merged and a - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, cur = [], lo
    for a, b in merged:
        if a > cur:
            out.append((cur, a, "plain"))
        out.append((a, b, "gfx"))
        cur = b
    if cur < hi:
        out.append((cur, hi, "plain"))
    return out


def zoom_pieces(plan, a, b):
    """A plain stretch split where the zoom changes: [(a, b, scale)]."""
    fps = plan["fps"]
    marks = {a, b}
    for z in plan["zooms"]:
        for t in (z["start"], z["end"]):
            f = frame_of(t, fps)
            if a < f < b:
                marks.add(f)
    edges = sorted(marks)
    out = []
    for s, e in zip(edges, edges[1:]):
        t = s / fps
        z = next((z["scale"] for z in plan["zooms"] if z["start"] <= t < z["end"]), 1.0)
        out.append((s, e, z))
    return out


def crop_filter(scale, face, w, h):
    """LongEdit's Footage: scale(zoom) with its origin at (face.cx, face.top) of the frame. The source region on
    screen is [o - o/s, o + (W - o)/s] on each axis: a crop of W/s x H/s at o * (1 - 1/s), scaled back up."""
    if abs(scale - 1.0) < 1e-6:
        return None
    ox, oy = face["cx"] * w, face["top"] * h
    cw, ch = w / scale, h / scale
    x, y = ox * (1 - 1 / scale), oy * (1 - 1 / scale)
    return f"crop={cw:.3f}:{ch:.3f}:{x:.3f}:{y:.3f},scale={w}:{h}:flags=bicubic"


def audio_graph(plan, edit, n_frames, base=1):
    """Inputs and filter for the whole edit's sound: voice + music bed + cues, summed (LongEdit plays them as
    separate <Audio> tracks at their given volume, no ducking)."""
    fps = plan["fps"]
    dur = n_frames / fps
    ins, parts, labels = [], [], []
    voice = plan.get("voice") or plan["video"]
    ins += ["-i", str(edit / voice)]
    # the video pieces come first, so the sound's inputs are numbered from base
    parts.append(f"[{base + len(ins) // 2 - 1}:a]aresample=48000,aformat=channel_layouts=stereo[v0]")
    labels.append("[v0]")
    tracks = ([plan["music"]] if plan.get("music") else []) + list(plan.get("sfx", []))
    for i, tr in enumerate(tracks):
        ins += ["-i", str(edit / tr["src"])]
        k = base + len(ins) // 2 - 1
        ms = max(0, round(tr.get("start", 0) * 1000))
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={tr.get('volume', 1)},"
                     f"adelay={ms}:all=1[t{i}]")
        labels.append(f"[t{i}]")
    parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,atrim=end={dur:.6f}[aout]")
    return ins, ";".join(parts)


def run(cmd, what):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ERROR {what}: {r.stderr[-600:]}")
    return r


def count_frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--frames", help="A-B: only these frames (a test), written to render-A-B.mp4")
    ap.add_argument("--bitrate", default=BITRATE)
    a = ap.parse_args()
    import edit as E
    edit = Path(a.edit).resolve()
    plan_path = edit / "plan.json"
    plan = json.loads(plan_path.read_text())
    if plan.get("composition") != "LongEdit":
        sys.exit("fast_render.py renders long-form plans (composition LongEdit); use edit.py render")
    fps, w, h = plan["fps"], plan["width"], plan["height"]
    lo, hi = (map(int, a.frames.split("-")) if a.frames else (0, plan["durationInFrames"]))
    out = edit / (f"render-{lo}-{hi}.mp4" if a.frames else "render.mp4")
    t0 = time.time()
    E.sync_renderer()
    pub = E.prepare_public(edit, plan, "")
    proxy = pub / plan["video"]
    parts = stretches(plan, lo, hi)
    gfx = [(s, e) for s, e, k in parts if k == "gfx"]
    plain = [(s, e) for s, e, k in parts if k == "plain"]
    print(f"{hi - lo} frames: {sum(e - s for s, e in gfx)} with graphics in {len(gfx)} stretches (Remotion), "
          f"{sum(e - s for s, e in plain)} plain in {len(plain)} (ffmpeg)", flush=True)
    tmp = Path(tempfile.mkdtemp(prefix="fast_render_", dir=edit))
    try:
        # the graphics' stretches: Remotion, in the background while ffmpeg cuts the plain ones
        gdir = tmp / "gfx"
        node = subprocess.Popen(["node", str(E.REMOTION / "render.mjs"), "ranges", str(pub), str(plan_path), str(gdir),
                                 *[f"{s}-{e}" for s, e in gfx]], cwd=E.REMOTION, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True) if gfx else None

        def plain_piece(job):
            i, s, e, z = job
            seg = tmp / f"p{i:04d}.mp4"
            t0_, t1_ = (s - 0.5) / fps, (e - 0.5) / fps
            vf = f"trim=start={max(0.0, t0_):.6f}:end={t1_:.6f},setpts=N/({fps})/TB"
            crop = crop_filter(z, plan["face"], w, h)
            vf += ("," + crop) if crop else ""
            run(["ffmpeg", "-v", "error", "-y", "-copyts", "-hwaccel", "videotoolbox", "-ss", f"{max(0.0, t0_ - 0.5):.6f}",
                 "-i", str(proxy), "-an", "-vf", vf + ",format=yuv420p", "-r", str(fps), "-c:v", "h264_videotoolbox",
                 "-b:v", "40M", str(seg)], f"plain frames {s}-{e}")
            got = count_frames(seg)
            if got != e - s:
                sys.exit(f"ERROR plain frames {s}-{e}: {got} frames, wanted {e - s}")
            return seg

        jobs, n = [], 0
        for s, e in plain:
            for ps, pe, z in zoom_pieces(plan, s, e):
                jobs.append((n, ps, pe, z))
                n += 1
        with cf.ThreadPoolExecutor(4) as ex:
            plain_files = dict(zip([(j[1], j[2]) for j in jobs], ex.map(plain_piece, jobs)))
        print(f"  plain: {len(jobs)} pieces in {time.time() - t0:.0f} s", flush=True)
        if node:
            for line in node.stdout:
                if line.startswith("range") or "Error" in line:
                    print("  " + line.rstrip(), flush=True)
            if node.wait():
                sys.exit("ERROR Remotion ranges failed")
        print(f"  graphics done at {time.time() - t0:.0f} s", flush=True)

        # in order: each plain stretch's pieces, each graphic stretch's file
        order = []
        for s, e, k in parts:
            if k == "gfx":
                order.append(gdir / f"{s}-{e}.mp4")
            else:
                order += [plain_files[(ps, pe)] for ps, pe, _ in zoom_pieces(plan, s, e)]
        # every piece is its own input, decoded on its own (the two encoders' headers differ, and a demuxer join of
        # them lost frames), then joined by the concat filter in order
        vins = [x for p in order for x in ("-i", str(p))]
        vfc = "".join(f"[{k}:v]format=yuv420p,setsar=1[p{k}];" for k in range(len(order)))
        vfc += "".join(f"[p{k}]" for k in range(len(order))) + f"concat=n={len(order)}:v=1:a=0,setpts=N/({fps})/TB[vout]"
        ains, afc = audio_graph(plan, edit, hi - lo, base=len(order))
        if lo:   # a test range: the sound starts at the range
            afc = afc.replace("atrim=end=", f"atrim=start={lo / fps:.6f}:end=").replace("[aout]", ",asetpts=PTS-STARTPTS[aout]")
            afc = afc.replace(f"end={(hi - lo) / fps:.6f}", f"end={hi / fps:.6f}")
        run(["ffmpeg", "-v", "error", "-y", *vins, *ains, "-filter_complex", vfc + ";" + afc,
             "-map", "[vout]", "-map", "[aout]", "-r", str(fps), "-c:v", "h264_videotoolbox", "-b:v", a.bitrate,
             "-maxrate", "16M", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
            "final encode")
        got = count_frames(out)
        if got != hi - lo:
            sys.exit(f"ERROR final: {got} frames, wanted {hi - lo}")
        mb = out.stat().st_size / 1e6
        print(f"rendered {out} ({got} frames, {mb:.0f} MB) in {(time.time() - t0) / 60:.1f} min")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def demo():
    plan = {"fps": 30, "durationInFrames": 900, "zooms": [{"start": 2.0, "end": 4.0, "scale": 1.15}],
            "graphics": [{"kind": "list", "start": 10.0, "end": 14.0}, {"kind": "phrase", "start": 14.5, "end": 16.0},
                         {"kind": "rows", "start": 25.0, "end": 27.0}]}
    s = stretches(plan)
    assert s == [(0, 300, "plain"), (300, 480, "gfx"), (480, 750, "plain"), (750, 810, "gfx"), (810, 900, "plain")], s
    assert zoom_pieces(plan, 0, 300) == [(0, 60, 1.0), (60, 120, 1.15), (120, 300, 1.0)]
    f = crop_filter(1.25, {"cx": 0.5, "top": 0.2}, 1920, 1080)
    assert f.startswith("crop=1536.000:864.000:192.000:43.200,"), f      # origin (960, 216): x = 960 * 0.2
    assert crop_filter(1.0, {"cx": 0.5, "top": 0.2}, 1920, 1080) is None
    assert stretches(plan, 280, 320) == [(280, 300, "plain"), (300, 320, "gfx")]
    print("fast_render demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        main()
