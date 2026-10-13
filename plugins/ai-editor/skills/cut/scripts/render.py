#!/usr/bin/env python3
"""Render the cut with plain ffmpeg: every kept span trimmed and joined.

    python3 render.py <source> <edit_dir> [--crf 18] [--no-hw]

Reads <edit_dir>/decisions.json and report.json, writes <edit_dir>/cut.mp4 at the
source resolution (rotation applied), H.264 + AAC.

How it stays exact on a big 4K source:
  - Each kept span is encoded on its own (video only), in parallel. One
    filter_complex over the whole 4K stream with 100 trims crawls.
  - Frames are counted per segment and again after joining. Frames in == frames out.
  - Audio is cut in ONE pass and muxed on at the end. Separate AAC tracks per
    segment add encoder padding at every join and drift by seconds.
  - Joins crossfade over 24 ms (each side reaches 12 ms past its cut into the source), so a join never clicks
    and a cut inside a sound (a restart said in one breath) blends instead of dipping to nothing and snapping
    back (Ayush, 2026-10-13: "a weird, harsh cut" at "teams that I worked at"). Length is unchanged: the
    overlap is exactly what each side reaches past its cut.
  - Keyframe every 15 frames, so the next step (Remotion) can seek quickly.
Never stream-copy (-c copy) across cuts: that snaps to keyframes, up to 2 s off.
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FADE_S = 0.008    # the first and last span fade in / out
XFADE_S = 0.012   # each side of a join reaches this far past its cut; the crossfade is twice it
LEAD_S = 0.5     # seek this far early, let the time-based trim pick the frames


def count_frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def starts(path):
    """(video stream start, file start) in seconds. With -copyts the video trim sees the stream's
    own timestamps, which can begin a frame or two in (B-frame delay, an edit list); the audio
    pass is rebased to the file start."""
    def one(entry, *sel):
        r = subprocess.run(["ffprobe", "-v", "error", *sel, "-show_entries", entry, "-of",
                            "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
        try:
            return float(r.stdout.split()[0])
        except (ValueError, IndexError):
            return 0.0
    return one("stream=start_time", "-select_streams", "v:0"), one("format=start_time")


def video_window(s, e, fps, vstart):
    """Trim times that select frames s..e-1 of the video stream exactly. Frame k sits at
    vstart + k/fps only up to the container's timestamp rounding (a 1/600 s timescale moves a
    29.97 fps frame by up to 0.8 ms either way), so a trim on the exact frame time keeps or drops
    that frame by the rounding: two edges rounded differently give N-1 or N+1. Half a frame
    early on both edges is immune to any rounding under half a frame."""
    return vstart + (s - 0.5) / fps, vstart + (e - 0.5) / fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("edit_dir")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--no-hw", action="store_true", help="skip hardware decode on a Mac")
    a = ap.parse_args()

    d = Path(a.edit_dir)
    rep = json.loads((d / "report.json").read_text())
    fps, frames = rep["fps"], rep["frames"]
    src, out = a.source, d / "cut.mp4"
    hw = sys.platform == "darwin" and not a.no_hw
    vstart, fstart = starts(src)
    off = vstart - fstart     # where frame 0 plays on the audio's timeline
    tmp = Path(tempfile.mkdtemp(prefix="cut_render_"))
    print(f"{len(frames)} spans, {sum(e - s for s, e in frames)} frames -> {out}", flush=True)

    def one(i):
        s, e = frames[i]
        t0, t1 = video_window(s, e, fps, vstart)
        seg = tmp / f"{i:05d}.mp4"
        # -copyts is load-bearing: without it the input seek rebases timestamps
        # to zero and the absolute trim picks the wrong footage at the right length.
        # Frame-numbered timestamps at an explicit -r: after setpts the frames carry no duration,
        # so without -r the muxer gives the last one ~0 s and FFmpeg 7's edit list ends on it,
        # dropping it on read. N/fps keeps the constant-rate clock from duplicating or dropping
        # frames over a 1/600 s source's jittered timestamps.
        cmd = ["ffmpeg", "-v", "error", "-y", "-copyts", *(["-hwaccel", "videotoolbox"] if hw else []),
               "-ss", f"{max(0.0, t0 - fstart - LEAD_S):.6f}", "-i", src, "-an",
               "-vf", f"trim=start={max(0.0, t0):.6f}:end={t1:.6f},setpts=N/({fps})/TB",
               "-r", str(fps), "-c:v", "libx264", "-crf", str(a.crf), "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-g", "15", str(seg)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            return f"span {i}: {r.stderr[-300:]}"
        got = count_frames(seg)
        return None if got == e - s else f"span {i}: {got} frames, wanted {e - s}"

    workers = max(2, (os.cpu_count() or 8) // (2 if hw else 4))
    with cf.ThreadPoolExecutor(workers) as ex:
        for n, err in enumerate(ex.map(one, range(len(frames))), 1):
            if err:
                sys.exit(f"ERROR {err}  (segments kept in {tmp})")
            if n % 20 == 0:
                print(f"  video {n}/{len(frames)}", flush=True)

    lst = tmp / "list.txt"
    # concat quoting: a ' in the temp path (a user name like O'Brien) is closed, escaped, reopened
    lst.write_text("".join("file '" + str(tmp / f"{i:05d}.mp4").replace("'", "'\\''") + "'\n"
                           for i in range(len(frames))))
    allv = tmp / "all.mp4"
    if subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                       "-c", "copy", str(allv)]).returncode:
        sys.exit("ERROR concat failed")
    want = sum(e - s for s, e in frames)
    if count_frames(allv) != want:
        sys.exit(f"ERROR concat lost frames (kept in {tmp})")

    print("  audio, one pass", flush=True)
    fc = audio_graph(frames, fps, off)
    aud = tmp / "a.m4a"
    if subprocess.run(["ffmpeg", "-v", "error", "-y", "-vn", "-i", src,
                       "-filter_complex", fc, "-map", "[ac]",
                       "-c:a", "aac", "-b:a", "192k", str(aud)]).returncode:
        sys.exit("ERROR audio pass failed")

    if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(allv), "-i", str(aud),
                       "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart",
                       str(out)]).returncode:
        sys.exit("ERROR mux failed")
    got = count_frames(out)
    print(f"  check: {got} frames of {want}, {want / fps:.2f}s")
    if got != want:
        sys.exit(f"ERROR frame mismatch (kept in {tmp})")
    shutil.rmtree(tmp)
    print(out)


def audio_graph(frames, fps, off, x=XFADE_S, sr=48000):
    """The audio filter graph. Each kept span reaches x past each inner cut and fades in and out over 2x; even
    spans go on one track and odd spans on another, each laid out with silence so the spans sit where they play,
    and the two tracks are summed. So every join is a 2x crossfade, the total length is exactly the kept
    frames' length, and the graph is two flat concats (a chain of 200 acrossfades ran 5x slower than real time)."""
    n = len(frames)
    if n == 1:
        s, e = frames[0]
        return (f"[0:a:0]atrim=start={off + s / fps:.6f}:end={off + e / fps:.6f},asetpts=PTS-STARTPTS,"
                f"aresample={sr},afade=t=in:d={FADE_S},afade=t=out:st={max(0.0, (e - s) / fps - FADE_S):.6f}:d={FADE_S}[ac]")
    X = round(x * sr)                         # samples, so every placement is exact
    lens = [round((e - s) / fps * sr) for s, e in frames]
    pos, p = [], 0
    for L in lens:
        pos.append(p)
        p += L
    total = p
    parts, tracks = [], {0: [], 1: []}
    cursor = {0: 0, 1: 0}
    for i, (s, e) in enumerate(frames):
        pre, post = (X if i > 0 else 0), (X if i < n - 1 else 0)
        start = pos[i] - pre                  # where this span's audio begins in the cut, samples
        length = lens[i] + pre + post
        t0 = off + s / fps - pre / sr
        fin = f"afade=t=in:ns={2 * pre}:curve=tri" if pre else f"afade=t=in:d={FADE_S}"
        fout = (f"afade=t=out:ss={length - 2 * post}:ns={2 * post}:curve=tri" if post
                else f"afade=t=out:st={max(0.0, length / sr - FADE_S):.6f}:d={FADE_S}")
        parts.append(f"[0:a:0]atrim=start={max(0.0, t0):.6f},asetpts=PTS-STARTPTS,aresample={sr},"
                     f"atrim=end_sample={length},{fin},{fout}[s{i}]")
        tr = i % 2
        gap = start - cursor[tr]
        if gap > 0:
            parts.append(f"aevalsrc=0:s={sr}:n={gap},atrim=end_sample={gap}[g{i}]")
            tracks[tr].append(f"[g{i}]")
        tracks[tr].append(f"[s{i}]")
        cursor[tr] = start + length
    for tr in (0, 1):
        tail = total - cursor[tr]
        if tail > 0:
            parts.append(f"aevalsrc=0:s={sr}:n={tail},atrim=end_sample={tail}[t{tr}]")
            tracks[tr].append(f"[t{tr}]")
        parts.append("".join(tracks[tr]) + f"concat=n={len(tracks[tr])}:v=0:a=1[k{tr}]")
    parts.append(f"[k0][k1]amix=inputs=2:normalize=0:duration=longest,atrim=end_sample={total}[ac]")
    return ";".join(parts)


def demo():
    g = audio_graph([(0, 30), (60, 90), (120, 150)], 30, 0.0)
    assert g.count("concat=") == 2 and "amix=inputs=2:normalize=0" in g and g.endswith("[ac]"), g
    assert "atrim=end_sample=144000[ac]" in g, g             # 3 s at 48 kHz exactly: the kept frames' length
    assert "[s1]" in g and "aevalsrc=0:s=48000:n=47424" in g, g   # span 1 on the odd track, after 0.988 s of silence
    assert "ns=1152:curve=tri" in g, g                         # 24 ms crossfades
    print("render demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
        sys.exit(0)
    main()
