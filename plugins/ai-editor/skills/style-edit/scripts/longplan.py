#!/usr/bin/env python3
"""Plan a long-form 16:9 edit in a measured style: board.json (what Claude decides) -> plan.json (LongEdit).

    python3 longplan.py edits/NAME [--style styles/axis-story/style.json] [--music audio/track.mp3]
    python3 longplan.py demo

Inputs in edits/NAME/: cut.mp4, words.json (the cut's words on its own timeline), decisions.json (the
kept spans: where the jump cuts are), face.json (face.py), board.json (written by Claude, shape below).
Writes plan.json (composition "LongEdit") and prints the pacing against the style's measured numbers,
then the plan checks. Exit 1 on a FAIL.

board.json. Every time is a quote of the words, never a number: "from"/"to" are the first and last words
the graphic covers, "on" the word an element draws on. "after": seconds on the cut picks a later match.
  {"graphics": [
    {"kind": "panel", "from": "...", "to": "...", "number": 1, "title": "Pitch",
     "diagram": {"type": "swoosh", "items": [{"text": "NAME", "on": "name"}, ...]}},   # diagrams.py templates
    {"kind": "panel", "from": "...", "to": "...", "title": "...", "bullets": [{"text": "...", "on": "..."}]},
    {"kind": "panel", "from": "...", "to": "...", "image": "images/site.png"},          # a supplied screenshot
    {"kind": "title", "from": "...", "to": "...", "heading": "...", "bullets": [{"text", "on"}]},
    {"kind": "quote", "from": "...", "to": "...", "text": "words he said, **key phrase** bold"},
    {"kind": "chapter", "on": "...", "number": 2, "title": "..."},       # only where a numbered part starts
    {"kind": "pills" | "buttons", "from": "...", "to": "...", "items": [{"text", "on"}]},
    {"kind": "label", "from": "...", "to": "...", "text": "..."},
    {"kind": "lower", "on": "...", "text": "..."}],
   "music": {"from": "<first words under music>", "to": "<last words under music>"}}

Copied from the references (styles/<name>/style.json, teardown.md), never invented: no captions; zoom
changes are hard punches on the jump cuts while the speaker is full frame; music a bed about 22 dB under
the voice from after the opening to before the close, no ducking; sound cues at the measured rate, on
full-screen cards.
"""
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagrams  # noqa: E402

REPO = HERE.parents[4]
DEFAULT_STYLE = REPO / "styles" / "axis-story" / "style.json"

HOLD = {"chapter": 3.5, "lower": 2.4}       # graphics with no "to": seconds up (references: chapter 3-5 s)
MIN_HOLD = {"panel": 4.0, "title": 4.0, "quote": 3.0, "pills": 2.5, "buttons": 2.5, "label": 2.0}
LEAD_S = 0.15                              # a graphic cuts in this long before its first word
TAIL_S = 0.35                              # and holds this long after its last
ZOOM_MIN_GAP_S = 4.0                       # between framing changes (first minute: 2.5)
MUSIC_FADE_S = 2.0
QUOTE_MAX_CHARS = 230                      # LongEdit shrinks a quote past ~135 characters to stay in 4 lines; past this it is too small
SFX_PER_MIN = 0.3                          # references: 0.1-0.4 a minute
WRITE_DONE_S = 1.2                         # a label writes on in about 1 s (references); it starts this long before the end at the latest


def norm(s):
    return re.sub(r"[^a-z0-9$%]+", "", str(s).lower().replace("-", ""))


def tokens(words):
    return [norm(w["text"]) for w in words]


def find(words, toks, phrase, after=0.0, last=False):
    """(start, end) of the first match of phrase at or after `after` seconds; last=True ends at its last word."""
    q = [norm(x) for x in re.split(r"\s+", phrase.strip()) if norm(x)]
    if not q:
        raise ValueError(f"empty quote {phrase!r}")
    for i in range(len(toks) - len(q) + 1):
        if words[i]["start"] + 1e-6 < after:
            continue
        if toks[i:i + len(q)] == q:
            return words[i]["start"], words[i + len(q) - 1]["end"]
    raise ValueError(f"quote not found in words.json: {phrase!r}" + (f" after {after}s" if after else ""))


def head_box(face_json):
    """The median head box (hair to chin), fractions of the frame."""
    boxes = [h["box"] for h in face_json.get("heads", []) if h.get("box")]
    if not boxes:
        return {"cx": 0.5, "top": 0.1, "h": 0.5, "bottom": 0.6}
    x, y, w, h = (statistics.median(b[i] for b in boxes) / 100 for i in range(4))
    return {"cx": round(x + w / 2, 4), "top": round(y, 4), "h": round(h, 4), "bottom": round(y + h, 4)}


def joins(spans):
    """Jump-cut times on the cut's timeline, from decisions.json."""
    t, out = 0.0, []
    for s in spans[:-1]:
        t += s["end"] - s["start"]
        out.append(round(t, 3))
    return out


def resolve(board, words):
    toks = tokens(words)
    out = []
    for g in board.get("graphics", []):
        k = g["kind"]
        after = g.get("after", 0.0)
        if "on" in g and "from" not in g:
            a, _ = find(words, toks, g["on"], after)
            start, end = a - LEAD_S, a - LEAD_S + g.get("hold", HOLD.get(k, 3.0))
        else:
            a, _ = find(words, toks, g["from"], after)
            _, b = find(words, toks, g["to"], a) if g.get("to") else (None, a + HOLD.get(k, 3.0))
            start, end = a - LEAD_S, b + TAIL_S
        start = max(0.0, start)
        # an element said near the end still finishes writing on (about 1 s) before the graphic leaves
        at = lambda phrase: round(min(find(words, toks, phrase, start)[0] - start, max(0.0, end - start - WRITE_DONE_S)), 3)  # noqa: E731
        item = {"kind": k, "start": round(start, 3), "end": round(end, 3)}
        if k == "panel":
            item.update({x: g[x] for x in ("number", "title") if g.get(x)})
            if "diagram" in g:
                d = dict(g["diagram"])
                for key in ("items", "left_items", "right_items"):
                    d[key] = [{"text": i["text"], "at": at(i["on"])} for i in d.get(key, [])]
                for key in ("center", "left", "right"):
                    if key in d:
                        d[key] = {"text": d[key]["text"], "at": at(d[key]["on"])}
                els = diagrams.build(d, seed=int(start * 10))
                item["body"] = {"type": "diagram", "els": els}
                item["_bounds"] = diagrams.bounds(els)
            elif "bullets" in g:
                item["body"] = {"type": "bullets", "heading": g.get("heading") or g.get("title", ""),
                                "bullets": [{"text": b["text"], "at": at(b["on"])} for b in g["bullets"]]}
                item.pop("title", None)
            elif "image" in g:
                item["body"] = {"type": "image", "src": g["image"], **({"focus": g["focus"]} if g.get("focus") else {})}
        elif k == "title":
            item.update(heading=g["heading"], bullets=[{"text": b["text"], "at": at(b["on"])} for b in g.get("bullets", [])])
        elif k in ("pills", "buttons"):
            item["items"] = [{"text": i["text"], "at": at(i["on"])} for i in g["items"]]
        elif k == "chapter":
            item.update(number=g["number"], title=g["title"])
        elif k in ("quote", "label", "lower"):
            item["text"] = g["text"]
        else:
            raise ValueError(f"unknown graphic kind {k!r}")
        out.append(item)
    return sorted(out, key=lambda g: g["start"])


BRIDGE_S = 1.0     # two full-frame graphics closer than this join: the speaker never flashes up for a moment


def bridge(graphics):
    full = [g for g in graphics if g["kind"] not in ("label", "buttons", "lower")]
    for a, b in zip(full, full[1:]):
        if 0 < b["start"] - a["end"] < BRIDGE_S:
            a["end"] = b["start"]
        elif 0 < a["end"] - b["start"] <= LEAD_S + TAIL_S:   # one's tail meets the next one's lead-in: cut there
            a["end"] = b["start"]
    return graphics


def plan_zooms(dur, graphics, cut_joins, scale):
    """Hard punches on the jump cuts while the speaker is full frame (the references change framing on
    their cuts, 2.8 a minute, busier in the first minute). Alternates in and out; a stretch under a graphic
    that hides the speaker resets to 1."""
    covered = lambda t: any(g["start"] - 0.05 <= t < g["end"] + 0.05 and g["kind"] not in ("label", "buttons", "lower")  # noqa: E731
                            for g in graphics)
    zooms, inn, last = [], False, -1e9
    start = None
    for t in cut_joins:
        gap = 2.5 if t < 60 else ZOOM_MIN_GAP_S
        if covered(t) or t - last < gap:
            continue
        # a graphic between the last change and this one already reset the framing
        if inn and any(last <= g["start"] < t for g in graphics if g["kind"] not in ("label", "buttons", "lower")):
            inn = False
        if not inn:
            start, inn = t, True
        else:
            zooms.append({"start": start, "end": t, "scale": scale})
            inn = False
        last = t
    if inn and start is not None:
        nxt = min([g["start"] for g in graphics if g["start"] > start and g["kind"] not in ("label", "buttons", "lower")]
                  + [dur])
        zooms.append({"start": start, "end": nxt, "scale": scale})
    # a zoom never runs under a full-frame graphic
    out = []
    for z in zooms:
        for g in graphics:
            if g["kind"] not in ("label", "buttons", "lower") and z["start"] < g["start"] < z["end"]:
                z = dict(z, end=g["start"])
        if z["end"] - z["start"] >= 1.0:
            out.append({k: round(v, 3) if isinstance(v, float) else v for k, v in z.items()})
    return out


REF_FACE_H = 0.242     # the references' speaker: YuNet face 24.2% of the frame high (look.md "close")
FACE_IN_HEAD = 1.5     # face.py's head box is the face grown 35% up and 15% down


def zoom_scale(head):
    """The references punch 1.25x from a face 24% of the frame high, so they never go tighter than about
    30%. Footage framed tighter than that gets only a small punch (at least 1.08x, or the framing change
    would not read), and never so far the head box leaves the frame (the zoom grows from the top of the head)."""
    face = head["h"] / FACE_IN_HEAD
    tight = REF_FACE_H * 1.25 / max(0.05, face)
    room = 1.0 / max(0.3, head["bottom"] - head["top"] + 0.05)
    return round(max(1.08, min(1.25, tight, room)), 2)


def music_bed(edit, track, start, end, dur, under_db):
    """.sfx/music-long.wav: the track looped to fill start..end, faded in and out, `under_db` under the
    cut's speech, no ducking (the references' bed sits at one level), silence elsewhere."""
    sys.path.insert(0, str(HERE))
    import sfx
    speech = sfx.speech_db(edit / "cut.mp4")
    probe = subprocess.run(["ffmpeg", "-v", "info", "-i", str(edit / track), "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    mean = float(re.search(r"mean_volume: (-?[\d.]+) dB", probe).group(1))
    gain = speech - under_db - mean
    length = end - start
    out = edit / ".sfx" / "music-long.wav"
    out.parent.mkdir(exist_ok=True)
    af = (f"volume={gain:.2f}dB,afade=t=in:st=0:d={MUSIC_FADE_S},afade=t=out:st={max(0, length - MUSIC_FADE_S):.3f}:d={MUSIC_FADE_S},"
          f"adelay={int(start * 1000)}:all=1,apad=whole_dur={dur:.3f}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(edit / track), "-t", f"{length:.3f}",
                    "-af", af, "-ar", "48000", "-ac", "2", str(out)], check=True)
    return out.relative_to(edit).as_posix(), round(gain, 1)


def place_sfx(edit, graphics, dur):
    """The references' rate (0.1-0.4 a minute), each on the cut to a full-screen card: a low hit on a chapter,
    a pop on a quote or pills. Never more than the rate allows; the earliest cards first."""
    n = max(0, round(dur / 60 * SFX_PER_MIN))
    if not n:
        return []
    kit = edit / ".sfx" / "kit.json"
    if not kit.exists():
        subprocess.run([sys.executable, str(HERE / "sfx.py"), "build", str(edit)], check=True, capture_output=True)
    cands = [g for g in graphics if g["kind"] in ("chapter", "quote", "pills")]
    pick = sorted(cands, key=lambda g: (g["kind"] != "chapter", g["start"]))[:n]
    cues = json.loads(kit.read_text())["cues"]
    out = []
    for g in sorted(pick, key=lambda g: g["start"]):
        name = "hit" if g["kind"] == "chapter" else "pop"
        out.append({"src": f".sfx/{name}.wav", "start": round(max(0.0, g["start"] - cues[name]["attack_s"]), 3)})
    return out


def checks(plan, head, style):
    """The instant plan checks: nothing overlaps, nothing runs off the frame, nothing sits on the face."""
    fails, warns = [], []
    gs = plan["graphics"]
    for a, b in zip(gs, gs[1:]):
        if b["start"] < a["end"] - 0.01:
            fails.append(f"{a['kind']} at {a['start']:.1f}s overlaps {b['kind']} at {b['start']:.1f}s")
    for g in gs:
        d = g["end"] - g["start"]
        if d < MIN_HOLD.get(g["kind"], 0) - 0.01:
            warns.append(f"{g['kind']} at {g['start']:.1f}s is up {d:.1f}s (references: at least {MIN_HOLD[g['kind']]} s)")
        if g.get("_bounds"):
            fails.append(f"panel at {g['start']:.1f}s: diagram text runs off the panel: {', '.join(g['_bounds'])}")
        if g["kind"] == "quote" and len(g["text"].replace("*", "")) > QUOTE_MAX_CHARS:
            fails.append(f"quote at {g['start']:.1f}s is {len(g['text'])} characters: over 4 lines (max {QUOTE_MAX_CHARS})")
        if g["kind"] == "buttons":
            rows = math.ceil(len(g["items"]) / 2)
            top = (706 - (rows - 2) * 130) / 1080 if rows > 2 else 706 / 1080
            if top < head["bottom"] - 0.02:
                fails.append(f"buttons at {g['start']:.1f}s sit on the face (head box ends {head['bottom'] * 100:.0f}% down, "
                             f"buttons start {top * 100:.0f}%): use pills (full screen) instead")
        if g["kind"] == "lower" and (1080 - 150 - 150) / 1080 < head["bottom"] - 0.02:
            fails.append(f"lower text at {g['start']:.1f}s sits on the chin (head box ends {head['bottom'] * 100:.0f}% down)")
        for t in [x["at"] for x in g.get("items", []) + g.get("bullets", [])]:
            if t > d:
                fails.append(f"{g['kind']} at {g['start']:.1f}s: an element draws on after the graphic ends")
    for z in plan["zooms"]:
        if z["start"] < 0 or z["end"] > plan["durationInFrames"] / plan["fps"] + 0.01:
            fails.append(f"zoom {z['start']:.1f}-{z['end']:.1f}s runs off the cut")
    return fails, warns


def pacing(plan, style):
    """The plan's numbers next to the references' (style.json "longform")."""
    lf = style.get("longform", {})
    dur = plan["durationInFrames"] / plan["fps"]
    full = [g for g in plan["graphics"] if g["kind"] not in ("label", "buttons", "lower")]
    share = 100 * sum(g["end"] - g["start"] for g in full) / dur
    gaps, t = [], 0.0
    for g in full:
        gaps.append(g["start"] - t)
        t = g["end"]
    gaps.append(dur - t)
    first = min([g["start"] for g in plan["graphics"]], default=None)
    lines = [f"graphics on screen  {share:.0f}%   (references: median {lf.get('graphics_on_screen_pct_median', '?')}%)",
             f"first graphic       {first:.1f}s  (references: median {lf.get('first_graphic_s_median', '?')} s)" if first is not None
             else "first graphic       none",
             f"speaker-only gaps   median {statistics.median(gaps):.1f}s, longest {max(gaps):.1f}s  (references: median "
             f"{lf.get('speaker_only_gap_s', {}).get('median', '?')} s, longest 13-27 s in two of three)",
             f"zoom changes        {2 * len(plan['zooms']) / (dur / 60):.1f} a minute  (references: 2.8)",
             f"sound cues          {len(plan.get('sfx', []))}  (references: 0.1-0.4 a minute)"]
    warn = []
    ref_med = lf.get("graphics_on_screen_pct_median")
    if ref_med and abs(share - ref_med) > 15:
        warn.append(f"graphics on screen {share:.0f}% is far from the references' {ref_med}%: "
                    + ("add a panel or quote where a sentence names a concept" if share < ref_med else "let the speaker carry more"))
    if max(gaps) > 30:
        warn.append(f"{max(gaps):.0f} s on the speaker with no graphic: the references' longest is 13-27 s (once 105 s)")
    return lines, warn


def build(edit, style_path=DEFAULT_STYLE, music=None):
    edit = Path(edit)
    words = [w for w in json.loads((edit / "words.json").read_text()) if w.get("type", "word") == "word"]
    spans = json.loads((edit / "decisions.json").read_text())
    board = json.loads((edit / "board.json").read_text())
    style = json.loads(Path(style_path).read_text())
    head = head_box(json.loads((edit / "face.json").read_text())) if (edit / "face.json").exists() else head_box({})
    meta = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(edit / "cut.mp4")],
                                     capture_output=True, text=True, check=True).stdout)
    num, den = meta["streams"][0]["r_frame_rate"].split("/")
    fps = round(float(num) / float(den), 3)
    dur = float(meta["format"]["duration"])
    graphics = bridge(resolve(board, words))
    for g in graphics:
        g["end"] = min(g["end"], dur)
    scale = zoom_scale(head)
    plan = {"composition": "LongEdit", "video": "cut.mp4", "width": 1920, "height": 1080, "fps": fps,
            "durationInFrames": int(round(dur * fps)), "face": {k: head[k] for k in ("cx", "top", "h")},
            "zooms": plan_zooms(dur, graphics, joins(spans), scale), "graphics": graphics, "cards": []}
    if music and board.get("music"):
        toks = tokens(words)
        a, _ = find(words, toks, board["music"]["from"])
        _, b = find(words, toks, board["music"]["to"], a)
        src, gain = music_bed(edit, music, max(0.0, a - 0.5), min(dur, b + 1.5), dur,
                              abs(style.get("sound", {}).get("music", {}).get("level_db") or 22))
        plan["music"] = {"src": src, "start": 0}
        print(f"music     {music} from {a:.1f}s to {b:.1f}s, {abs(style['sound']['music']['level_db'])} dB under the voice")
    plan["sfx"] = place_sfx(edit, graphics, dur)
    fails, warns = checks(plan, head, style)
    lines, pw = pacing(plan, style)
    for g in plan["graphics"]:
        g.pop("_bounds", None)
    (edit / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"plan      {len(graphics)} graphics, {len(plan['zooms'])} zooms (x{scale}), {len(plan['sfx'])} sound cues "
          f"-> {edit / 'plan.json'}")
    print("\n".join("  " + x for x in lines))
    for w in warns + pw:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")
    return 1 if fails else 0


def demo():
    words = [{"text": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate(
        "back when I sold at Google Cloud I sent a cold email . it led to a meeting and a pilot and then growth".split())]
    board = {"graphics": [{"kind": "panel", "from": "it led", "to": "growth", "title": "Result",
                           "diagram": {"type": "swoosh", "items": [{"text": "Meeting", "on": "meeting"}, {"text": "Pilot", "on": "pilot"}]}},
                          {"kind": "lower", "on": "cold email", "text": "Cold email"}]}
    gs = resolve(board, words)
    assert [g["kind"] for g in gs] == ["lower", "panel"], gs
    p = gs[1]
    assert abs(p["start"] - (13 * 0.4 - LEAD_S)) < 1e-6 and p["body"]["type"] == "diagram", p
    assert any(e.get("text") == "MEETING" for e in p["body"]["els"])
    try:
        find(words, tokens(words), "not said")
        raise AssertionError("a missing quote must fail")
    except ValueError:
        pass
    head = {"cx": 0.46, "top": 0.05, "h": 0.75, "bottom": 0.8}
    assert zoom_scale(head) <= 1.25 and zoom_scale(head) >= 1.06
    z = plan_zooms(60, [{"kind": "panel", "start": 20, "end": 30}], [3, 6, 9, 12, 22, 33, 40, 50], 1.15)
    assert z and all(not (20 <= x["start"] < 30) for x in z), z
    assert all(x["end"] <= 20 or x["start"] >= 30 for x in z), z
    plan = {"graphics": [{"kind": "buttons", "start": 1, "end": 4, "items": [{"text": "a", "at": 0}]}], "zooms": [],
            "durationInFrames": 300, "fps": 30}
    assert checks(plan, head, {})[0], "buttons over a tight head must fail"
    print("longplan ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("edit")
        ap.add_argument("--style", default=str(DEFAULT_STYLE))
        ap.add_argument("--music", help="a track in the edit folder, e.g. audio/track.mp3")
        a = ap.parse_args()
        sys.exit(build(a.edit, a.style, a.music))
