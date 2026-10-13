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

The sdr-mastery style's white pages (Pages.tsx). A "said" field is the words as they should read, either a
string said nearly verbatim (its time is found by its opening words) or {"text": "...", "on": "<quote>"}:
    {"kind": "list", "from", "to", "heading": "...", "sub": said, "items": [said, ...], "marker": "number|dot|none", "card": false}
    {"kind": "rows", "from", "to", "items": [{"label": "Part 1", "text": "The list", "on": "<quote>"}], "preview": false}
        preview: every row up from the start, a row's text blurred until said (the part card); a row with no "on" stays blurred
    {"kind": "dialogue", "from", "to", "turns": [{"head": "Let's say someone said:", "line": said, "head_on": "<quote>"}]}
    {"kind": "rule", "from", "to", "heading": "...", "items": [said], "dots": false, "card": true}
    {"kind": "acronym", "from", "to", "word": "BANT", "items": [{"text": "Budget", "on": "budget"}, ...]}
    {"kind": "illustration", "from", "to", "image": "images/x.png", "line": said, "side_image": "...", "side_text": said}
    {"kind": "shot", "from", "to", "image": "images/site.png", "fit": "full|frame", "scroll": false}
    {"kind": "phrase", "from", "to", "lines": [{"text": "Most people mess up"}, {"text": "because they start off wrong", "italic": true}]}
A style lists the kinds it uses (style.json design.kinds); a board kind outside that list fails the plan.

Copied from the references (styles/<name>/style.json, teardown.md), never invented: no captions; zoom
changes are hard punches on the jump cuts while the speaker is full frame, at the style's rate; music a bed
under the voice at the style's level from after the opening to before the close, no ducking; sound cues at
the measured rate, on full-screen cards.
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

OVERLAYS = ("label", "buttons", "lower", "phrase")   # drawn over the speaker; every other kind fills the frame
PAGES = ("list", "rows", "dialogue", "rule", "acronym", "illustration", "shot", "phrase")   # Pages.tsx: words timed as said
HOLD = {"chapter": 3.5, "lower": 2.4}       # graphics with no "to": seconds up (references: chapter 3-5 s)
MIN_HOLD = {"panel": 4.0, "title": 4.0, "quote": 3.0, "pills": 2.5, "buttons": 2.5, "label": 2.0}
LEAD_S = 0.15                              # a graphic cuts in this long before its first word
TAIL_S = 0.35                              # and holds this long after its last
OVERLAY_EXIT_S = 0.3                       # overlays hold this much longer: their soft exit (0.5 s) starts after the last word
ZOOM_MIN_GAP_S = 7.0                       # between framing changes (first minute: 2.5); references: 2.8 a minute
MUSIC_FADE_S = 2.0
QUOTE_MAX_CHARS = 230                      # LongEdit shrinks a quote past ~135 characters to stay in 4 lines; past this it is too small
SFX_PER_MIN = 0.3                          # references: 0.1-0.4 a minute
SILENT_MAX_S = 1.2                         # never graphics on screen with no talking (Ayush, 2026-10-10)
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


def timed_words(shown, words, toks, start):
    """[{"text", "at"}]: each word to show, at the moment it is said (seconds into the graphic). `shown` is a
    string of the words as they should read ("$100M SaaS company"), matched in order to the spoken words from
    `start` on; a word not said as written ("$100M" for "$100 million") takes the next spoken word's time. Or a
    list of {"text", "on"} with an explicit quote each."""
    if isinstance(shown, list):
        return [{"text": w["text"], "at": round(find(words, toks, w["on"], start)[0] - start, 3)} for w in shown]
    i = next((k for k, w in enumerate(words) if w["start"] + 1e-6 >= start), len(words))
    out = []
    for text in shown.split():
        n = norm(text)
        near = range(i, min(len(words), i + 6))
        j = next((k for k in near if toks[k] == n), None)
        if j is None and len(n) >= 2:   # written short ("$100M" for "$100 million"): the word it starts like
            j = next((k for k in near if len(toks[k]) >= 2 and (n.startswith(toks[k]) or toks[k].startswith(n))), None)
        if j is None:
            j = min(i, len(words) - 1)
            i += 1 if norm(text) else 0
        else:
            i = j + 1
        out.append({"text": text, "at": round(max(0.0, words[j]["start"] - start), 3)})
    for k, text in enumerate(shown.split()):   # a sign that is not a word ("->") arrives with the word after it
        if not norm(text) and k + 1 < len(out):
            out[k]["at"] = out[k + 1]["at"]
    for a, b in zip(out, out[1:]):       # never out of order
        b["at"] = max(b["at"], a["at"])
    return out


READ_MIN_S = 2.0        # a graphic, once all of it is up, stays at least this long (Ayush, 2026-10-10: too short to read
READ_PER_WORD_S = 0.3   # is not worth having), and this much longer for each word on it
STAGGER_S = 0.35        # items brought forward to make that room arrive this far apart
EASE_IN_S = 0.55        # an item takes this long to settle (LongEdit POP_S)


def read_s(items):
    return max(READ_MIN_S, READ_PER_WORD_S * sum(len(i["text"].split()) for i in items))


def readable(items, dur):
    """Items whose last one would leave too little time to read the whole graphic come in earlier, one after
    another from the graphic's start, so the full set is up for read_s before the graphic leaves (its soft exit
    not counted)."""
    if not items:
        return items
    latest = dur - OVERLAY_EXIT_S - 0.2 - EASE_IN_S - read_s(items)   # settled (not just arriving) for read_s
    n = len(items)
    out = [dict(it, at=round(max(0.15 + i * STAGGER_S * 0.5, min(it["at"], latest - (n - 1 - i) * STAGGER_S)), 3))
           for i, it in enumerate(items)]
    for a, b in zip(out, out[1:]):
        b["at"] = max(b["at"], a["at"] + 0.1)
    return out


def line_start(line, words, toks, after):
    """When a script line starts being said: the first place at or after `after` where its opening words are
    spoken in order (three, else two, else one). A line not said fails the plan rather than guess a time."""
    q = [norm(x) for x in line.split() if norm(x)]
    i0 = next((k for k, w in enumerate(words) if w["start"] + 1e-6 >= after), len(words))
    for n in (3, 2, 1):
        if len(q) < n:
            continue
        k = next((k for k in range(i0, len(words) - n + 1) if toks[k:k + n] == q[:n]), None)
        if k is not None:
            return words[k]["start"]
    raise ValueError(f"script line not found in words.json after {after:.1f}s: {line!r}")


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
            # an overlay on the speaker also holds through its 0.5 s soft exit (LongEdit EXIT_S), so the last word
            # is never fading while it is still being said
            start, end = a - LEAD_S, b + TAIL_S + (OVERLAY_EXIT_S if k in OVERLAYS else 0)
        start = max(0.0, start)
        # an element said near the end still finishes writing on (about 1 s) before the graphic leaves
        latest = max(0.0, end - start - WRITE_DONE_S)
        at = lambda phrase: round(min(find(words, toks, phrase, start)[0] - start, latest), 3)  # noqa: E731
        cursor = [start]

        def said(spec):
            """A "said" field -> [{"text", "at"}], each word at the moment it is said (seconds into the graphic), found
            after the last one placed, so a list's lines are matched in the order he says them."""
            text, on = (spec, None) if isinstance(spec, str) else (spec["text"], spec.get("on"))
            t0 = find(words, toks, on, cursor[0])[0] if on else line_start(text, words, toks, cursor[0])
            ws = timed_words(text, words, toks, t0)
            cursor[0] = t0 + ws[-1]["at"] + 0.01 if ws else t0
            return [dict(w, at=round(max(0.0, min(w["at"] + t0 - start, latest)), 3)) for w in ws]
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
                item["body"] = {"type": "image", "src": g["image"], **({"focus": g["focus"]} if g.get("focus") else {}),
                                **({"fit": g["fit"]} if g.get("fit") else {})}
        elif k == "title":
            item.update(heading=g["heading"], bullets=[{"text": b["text"], "at": at(b["on"])} for b in g.get("bullets", [])])
        elif k in ("pills", "buttons"):
            item["items"] = readable([{"text": i["text"], "at": at(i["on"])} for i in g["items"]], end - start)
        elif k == "chapter":
            item.update(number=g["number"], title=g["title"])
        elif k == "lower":
            item["words"] = timed_words(g.get("words") or g["text"], words, toks, start)
        elif k == "script":
            cursor, lines = start, []
            for line in g["lines"]:
                t0 = line_start(line, words, toks, cursor)   # where this line is said, found by its opening words
                ws = [dict(w, at=round(w["at"] + t0 - start, 3)) for w in timed_words(line, words, toks, t0)]
                lines.append(ws)
                cursor = start + ws[-1]["at"] + 0.01
            item["lines"] = lines
            item["heading"] = g.get("heading", "")
        elif k in ("quote", "label"):
            item["text"] = g["text"]
        elif k == "list":
            item.update(heading=g.get("heading", ""), marker=g.get("marker", "dot"), card=bool(g.get("card")))
            if g.get("sub"):
                item["sub"] = said(g["sub"])
            item["items"] = [said(x) for x in g["items"]]
        elif k == "rows":
            rows = []
            for r in g["items"]:
                if r.get("on"):
                    t0 = find(words, toks, r["on"], cursor[0])[0]
                    cursor[0] = t0 + 0.01
                    rows.append({"label": r["label"], "at": round(min(t0 - start, latest), 3),
                                 "text": [dict(w, at=round(min(w["at"] + t0 - start, latest), 3)) for w in timed_words(r["text"], words, toks, t0)]})
                elif g.get("preview"):    # a part still to come: up and blurred, never said here
                    rows.append({"label": r["label"], "at": None, "text": [{"text": x, "at": 1e6} for x in r["text"].split()]})
                else:
                    raise ValueError(f"rows at {start:.1f}s: row {r['label']!r} has no \"on\" (only a preview row may stay unsaid)")
            item.update(items=rows, preview=bool(g.get("preview")))
        elif k == "dialogue":
            turns = []
            for tn in g["turns"]:
                head_at = at(tn["head_on"]) if tn.get("head_on") else None
                line = said(tn["line"])
                turns.append({"head": tn["head"], "head_at": head_at if head_at is not None else round(max(0.0, line[0]["at"] - 0.6), 3),
                              "line": line})
            item["turns"] = turns
        elif k == "rule":
            item.update(heading=g["heading"], items=[said(x) for x in g.get("items", [])], dots=bool(g.get("dots")),
                        card=bool(g.get("card", True)))
        elif k == "acronym":
            item.update(word=g["word"], items=[{"text": i["text"], "at": at(i["on"])} for i in g["items"]])
            if len(g["items"]) != len(g["word"]):
                raise ValueError(f"acronym {g['word']!r}: {len(g['items'])} words for {len(g['word'])} letters")
        elif k == "illustration":
            item.update(image=g["image"], line=said(g["line"]))
            if g.get("side_image"):
                item["side_image"] = g["side_image"]
            if g.get("side_text"):
                item["side_text"] = said(g["side_text"])
            if g.get("side_image") or g.get("side_text"):
                item["side_at"] = at(g["side_on"]) if g.get("side_on") else (item["side_text"][0]["at"] if g.get("side_text") else 0.0)
        elif k == "shot":
            item.update(image=g["image"], fit=g.get("fit", "full"), scroll=bool(g.get("scroll")))
        elif k == "phrase":
            item["lines"] = [{"words": said(ln), "italic": bool(ln.get("italic"))} if isinstance(ln, dict)
                             else {"words": said(ln), "italic": False} for ln in g["lines"]]
        else:
            raise ValueError(f"unknown graphic kind {k!r}")
        out.append(item)
    return sorted(out, key=lambda g: g["start"])


BRIDGE_S = 1.0     # two full-frame graphics closer than this join: the speaker never flashes up for a moment


def bridge(graphics):
    for a, b in zip(graphics, graphics[1:]):
        if 0 < a["end"] - b["start"] <= LEAD_S + TAIL_S + OVERLAY_EXIT_S:   # a tail meets the next lead-in: cut there
            a["end"] = b["start"]
    full = [g for g in graphics if g["kind"] not in OVERLAYS]
    for a, b in zip(full, full[1:]):
        if 0 < b["start"] - a["end"] < BRIDGE_S:
            a["end"] = b["start"]
    return graphics


def zoom_gap(style):
    """Seconds between framing changes after the first minute: 7 s at axis-story's 2.8 punches a minute, shorter
    in proportion for a style that punches more often (sdr-mastery: 4.9 a minute -> 4 s)."""
    per_min = (style.get("zoom") or {}).get("per_min") or 2.8
    return round(ZOOM_MIN_GAP_S * 2.8 / per_min, 2)


def plan_zooms(dur, graphics, cut_joins, scale, gap_s=ZOOM_MIN_GAP_S):
    """Hard punches on the jump cuts while the speaker is full frame (the references change framing on
    their cuts at the style's rate, busier in the first minute). Alternates in and out; a stretch under a
    graphic that hides the speaker resets to 1."""
    covered = lambda t: any(g["start"] - 0.05 <= t < g["end"] + 0.05 and g["kind"] not in OVERLAYS  # noqa: E731
                            for g in graphics)
    zooms, inn, last = [], False, -1e9
    start = None
    for t in cut_joins:
        gap = 2.5 if t < 60 else gap_s
        if covered(t) or t - last < gap:
            continue
        # a graphic between the last change and this one already reset the framing
        if inn and any(last <= g["start"] < t for g in graphics if g["kind"] not in OVERLAYS):
            inn = False
        if not inn:
            start, inn = t, True
        else:
            zooms.append({"start": start, "end": t, "scale": scale})
            inn = False
        last = t
    if inn and start is not None:
        nxt = min([g["start"] for g in graphics if g["start"] > start and g["kind"] not in OVERLAYS]
                  + [dur])
        zooms.append({"start": start, "end": nxt, "scale": scale})
    # a zoom never runs under a full-frame graphic
    out = []
    for z in zooms:
        for g in graphics:
            if g["kind"] not in OVERLAYS and z["start"] < g["start"] < z["end"]:
                z = dict(z, end=g["start"])
        if z["end"] - z["start"] >= 1.0:
            out.append({k: round(v, 3) if isinstance(v, float) else v for k, v in z.items()})
    return out


REF_FACE_H = 0.242     # the references' speaker: YuNet face 24.2% of the frame high (look.md "close")
FACE_IN_HEAD = 1.5     # face.py's head box is the face grown 35% up and 15% down


def zoom_scale(head, ref_face_h=REF_FACE_H, ref_scale=1.25):
    """The references punch `ref_scale` from a face `ref_face_h` of the frame high (axis-story: 1.25x from 24%,
    so never tighter than about 30%; sdr-mastery: 1.15x from 41%). Footage framed tighter than the reference
    gets a smaller punch (at least 1.08x, or the framing change would not read), and never so far the head box
    leaves the frame (the zoom grows from the top of the head)."""
    face = head["h"] / FACE_IN_HEAD
    tight = ref_face_h * ref_scale / max(0.05, face)
    room = 1.0 / max(0.3, head["bottom"] - head["top"] + 0.05)
    return round(max(1.08, min(ref_scale, tight, room)), 2)


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


def voice_track(edit):
    """.sfx/voice.wav: the cut's voice as its own stereo track, both sides at full level. LongEdit plays it for
    the whole cut so a full-screen card never silences it, and a mono track handed to the renderer comes out
    3 dB down (measured)."""
    out = edit / ".sfx" / "voice.wav"
    out.parent.mkdir(exist_ok=True)
    if not out.exists() or out.stat().st_mtime < (edit / "cut.mp4").stat().st_mtime:
        ch = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of",
                             "csv=p=0", str(edit / "cut.mp4")], capture_output=True, text=True).stdout.strip()
        af = ["-af", "pan=stereo|c0=c0|c1=c0"] if ch == "1" else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(edit / "cut.mp4"), "-vn", *af, "-ar", "48000", "-c:a", "pcm_s16le",
                        str(out)], check=True)
    return out.relative_to(edit).as_posix()


def pick_sfx(graphics, dur, conf=None):
    """Which full-screen cards get a sound cue. axis-story (no "sfx" in style.json longform): 0.3 a minute, a low
    hit on a chapter, a pop on a quote or pills, chapters then the earliest cards. A style's own
    {"per_min", "on": [kinds], "name", "opening"}: its rate, the first `opening` cards in the first minute (the
    sdr-mastery reference bunches its impacts there), the rest spread evenly over the later cards."""
    if not conf:
        n = max(0, round(dur / 60 * SFX_PER_MIN))
        cands = [g for g in graphics if g["kind"] in ("chapter", "quote", "pills")]
        pick = sorted(cands, key=lambda g: (g["kind"] != "chapter", g["start"]))[:n]
        return [(g, "hit" if g["kind"] == "chapter" else "pop") for g in sorted(pick, key=lambda g: g["start"])]
    n = max(0, round(dur / 60 * conf["per_min"]))
    cands = [g for g in graphics if g["kind"] in conf["on"]]
    early = [g for g in cands if g["start"] < 60][:min(n, conf.get("opening", 0))]
    later = [g for g in cands if g not in early]
    k = n - len(early)
    spread = [later[round(i * (len(later) - 1) / max(1, k - 1))] for i in range(k)] if k > 0 and later else []
    pick = sorted({id(g): g for g in early + spread}.values(), key=lambda g: g["start"])
    return [(g, conf.get("name", "hit")) for g in pick]


def place_sfx(edit, graphics, dur, conf=None):
    """Sound cues on the cut to full-screen cards, at the style's measured rate (pick_sfx)."""
    pick = pick_sfx(graphics, dur, conf)
    if not pick:
        return []
    kit = edit / ".sfx" / "kit.json"
    if not kit.exists():
        subprocess.run([sys.executable, str(HERE / "sfx.py"), "build", str(edit)], check=True, capture_output=True)
    cues = json.loads(kit.read_text())["cues"]
    return [{"src": f".sfx/{name}.wav", "start": round(max(0.0, g["start"] - cues[name]["attack_s"]), 3)} for g, name in pick]


def page_words(g):
    """Every timed word or element of a Pages.tsx graphic."""
    k = g["kind"]
    if k == "list":
        return g.get("sub", []) + [w for it in g["items"] for w in it]
    if k == "rows":
        return [w for r in g["items"] for w in r["text"]]
    if k == "dialogue":
        return [{"at": t["head_at"]} for t in g["turns"]] + [w for t in g["turns"] for w in t["line"]]
    if k == "rule":
        return [w for it in g["items"] for w in it]
    if k == "acronym":
        return g["items"]
    if k == "illustration":
        return g["line"] + g.get("side_text", []) + ([{"at": g["side_at"]}] if "side_at" in g else [])
    if k == "phrase":
        return [w for ln in g["lines"] for w in ln["words"]]
    return []


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
        if g["kind"] in ("buttons", "lower", "script", "phrase"):
            room = 990 - (head["top"] + head["h"] * 0.9) * 1080 - 24     # under the chin, above the frame's foot
            if room < 60:
                fails.append(f"{g['kind']} at {g['start']:.1f}s: no room under the chin for words over the speaker "
                             f"({room:.0f} px): use a quote or panel instead")
        allowed = (style.get("design") or {}).get("kinds")
        if allowed and g["kind"] not in allowed:
            fails.append(f"{g['kind']} at {g['start']:.1f}s is not a graphic this style uses ({', '.join(allowed)})")
        if g["kind"] in PAGES:
            # words arrive as they are said, so the eye reads along: the whole graphic need only stay READ_MIN_S
            # once its last word is in (overlays: before their soft exit)
            ats = [w["at"] for w in page_words(g) if w["at"] < 1e5]
            if ats:
                left = d - max(ats) - 0.45 - (OVERLAY_EXIT_S + 0.2 if g["kind"] in OVERLAYS else 0)
                if left < READ_MIN_S - 0.05:
                    fails.append(f"{g['kind']} at {g['start']:.1f}s is all up for only {left:.1f}s after its last word: too short "
                                 f"to read (at least {READ_MIN_S:.1f} s). End it later or leave it out")
            continue
        items = g.get("items") or g.get("bullets") or []
        if items and d - max(x["at"] for x in items) - EASE_IN_S - (0.5 if g["kind"] in ("lower", "buttons", "label") else 0) < read_s(items) - 0.05:
            fails.append(f"{g['kind']} at {g['start']:.1f}s is all up for only {d - max(x['at'] for x in items):.1f}s: too short to "
                         f"read (at least {read_s(items):.1f} s). Start it earlier in the sentence or leave it out")
        for t in [x["at"] for x in g.get("items", []) + g.get("bullets", [])]:
            if t > d:
                fails.append(f"{g['kind']} at {g['start']:.1f}s: an element draws on after the graphic ends")
    for g in gs:
        said = [w for w in plan.get("_words", []) if w["end"] > g["start"] and w["start"] < g["end"]]
        if not said:
            fails.append(f"{g['kind']} at {g['start']:.1f}s is up with no one talking")
            continue
        edges = [g["start"]] + [x for w in said for x in (w["start"], w["end"])] + [g["end"]]
        quiet = max(b - a for a, b in zip(edges[::2], edges[1::2]))
        if quiet > SILENT_MAX_S:
            warns.append(f"{g['kind']} at {g['start']:.1f}s holds {quiet:.1f}s with no one talking (at most {SILENT_MAX_S} s)")
    for z in plan["zooms"]:
        if z["start"] < 0 or z["end"] > plan["durationInFrames"] / plan["fps"] + 0.01:
            fails.append(f"zoom {z['start']:.1f}-{z['end']:.1f}s runs off the cut")
    return fails, warns


def pacing(plan, style):
    """The plan's numbers next to the references' (style.json "longform")."""
    lf = style.get("longform", {})
    dur = plan["durationInFrames"] / plan["fps"]
    full = [g for g in plan["graphics"] if g["kind"] not in OVERLAYS]
    share = 100 * sum(g["end"] - g["start"] for g in full) / dur
    gaps, t = [], 0.0
    for g in full:
        gaps.append(g["start"] - t)
        t = g["end"]
    gaps.append(dur - t)
    first = min([g["start"] for g in plan["graphics"]], default=None)
    lines = [f"graphics on screen  {share:.0f}%   (for information: the references' median is {lf.get('graphics_on_screen_pct_median', '?')}%)",
             f"first graphic       {first:.1f}s  (references: median {lf.get('first_graphic_s_median', '?')} s)" if first is not None
             else "first graphic       none",
             f"speaker-only gaps   median {statistics.median(gaps):.1f}s, longest {max(gaps):.1f}s  (references: median "
             f"{lf.get('speaker_only_gap_s', {}).get('median', '?')} s, longest {lf.get('speaker_only_gap_s', {}).get('max', '13-27')} s)",
             f"zoom changes        {2 * len(plan['zooms']) / (dur / 60):.1f} a minute  (references: {(style.get('zoom') or {}).get('per_min', 2.8)})",
             f"sound cues          {len(plan.get('sfx', []))}  (references: "
             f"{(lf.get('sfx') or {}).get('per_min', '0.1-0.4')} a minute)"]
    # information only: graphics go where they make what is said easier to understand, never to fill time or
    # to reach the references' share (Ayush, 2026-10-10)
    return lines, []


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
        if g["kind"] in ("pills", "buttons"):   # after trimming: the room to read is what is left
            g["items"] = readable(g["items"], g["end"] - g["start"])
    face_ref = (style.get("face") or {}).get("height_pct")
    scale = zoom_scale(head, face_ref / 100 if face_ref else REF_FACE_H, (style.get("zoom") or {}).get("scale") or 1.25)
    plan = {"composition": "LongEdit", "video": "cut.mp4", "width": 1920, "height": 1080, "fps": fps,
            "durationInFrames": int(round(dur * fps)), "face": {k: head[k] for k in ("cx", "top", "h")},
            "zooms": plan_zooms(dur, graphics, joins(spans), scale, zoom_gap(style)), "graphics": graphics, "cards": []}
    if (style.get("design") or {}).get("plan_palette"):    # the style's own colours (sdr-mastery's reds and ink)
        plan["palette"] = style["design"]["plan_palette"]
    if music and board.get("music"):
        toks = tokens(words)
        a, _ = find(words, toks, board["music"]["from"])
        _, b = find(words, toks, board["music"]["to"], a)
        src, gain = music_bed(edit, music, max(0.0, a - 0.5), min(dur, b + 1.5), dur,
                              abs(style.get("sound", {}).get("music", {}).get("level_db") or 22))
        plan["music"] = {"src": src, "start": 0}
        print(f"music     {music} from {a:.1f}s to {b:.1f}s, {abs(style['sound']['music']['level_db'])} dB under the voice")
    plan["voice"] = voice_track(edit)
    plan["sfx"] = place_sfx(edit, graphics, dur, style.get("longform", {}).get("sfx"))
    plan["_words"] = words
    fails, warns = checks(plan, head, style)
    plan.pop("_words")
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
    plan["_words"] = [{"text": "a", "start": 1.5, "end": 3.5}]
    assert not checks(plan, head, {})[0], "pills under a chin at 72% fit"
    assert checks(plan, {"cx": 0.5, "top": 0.2, "h": 0.75, "bottom": 0.95}, {})[0], "no room under a low chin must fail"
    plan["_words"] = []
    assert any("no one talking" in f for f in checks(plan, head, {})[0]), "a graphic over silence must fail"
    spoken = [{"text": t, "start": 10 + i, "end": 10.5 + i} for i, t in enumerate("at a $100 million SaaS company".split())]
    ws = timed_words("$100M SaaS company", spoken, tokens(spoken), 10.0)
    assert [w["at"] for w in ws] == [2.0, 4.0, 5.0], ws     # "$100M" lands on "$100", as it is said

    # the sdr-mastery pages: every word timed as it is said, lines matched in the order he says them
    talk = [{"text": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(
        ("so the list matters . things to do : get specific on your icp , use a simple structure . part one is "
         "the list building . let's say someone said hey send me an email and I will say happy to . "
         "budget authority need timing . most people mess up because they start off wrong . end of it all here now").split())]
    page_board = {"graphics": [
        {"kind": "list", "from": "things to do", "to": "simple structure", "heading": "Things to do while list building:",
         "marker": "number", "items": ["Get specific on your ICP", {"text": "Use a simple structure", "on": "use a simple"}]},
        {"kind": "rows", "from": "part one", "to": "list building", "preview": True,
         "items": [{"label": "Part 1", "text": "The list building", "on": "list building"}, {"label": "Part 2", "text": "The script"}]},
        {"kind": "dialogue", "from": "let's say", "to": "happy to", "turns": [
            {"head": "Let's say someone said:", "line": {"text": "Hey, send me an email", "on": "hey send"}, "head_on": "let's say"},
            {"head": "I will say:", "line": {"text": "Happy to", "on": "happy to"}}]},
        {"kind": "acronym", "from": "budget", "to": "timing", "word": "BANT",
         "items": [{"text": t.title(), "on": t} for t in ("budget", "authority", "need", "timing")]},
        {"kind": "phrase", "from": "most people", "to": "off wrong", "lines": [{"text": "Most people mess up"},
                                                                             {"text": "because they start off wrong", "italic": True}]}]}
    pg = resolve(page_board, talk)
    lst, rows, dia, acr, phr = pg
    assert [w["text"] for w in lst["items"][0]] == "Get specific on your ICP".split(), lst
    assert lst["items"][1][0]["at"] > lst["items"][0][-1]["at"], "the second line is timed after the first"
    assert rows["items"][0]["at"] is not None and rows["items"][1]["at"] is None, rows     # Part 2 stays blurred
    assert dia["turns"][1]["head_at"] < dia["turns"][1]["line"][0]["at"], dia
    assert [i["at"] for i in acr["items"]] == sorted(i["at"] for i in acr["items"]), acr
    assert phr["lines"][1]["italic"] and phr["lines"][1]["words"][0]["text"] == "because", phr
    sty = {"design": {"kinds": ["list", "rows"]}}
    bad = {"graphics": [dict(acr)], "zooms": [], "durationInFrames": 3000, "fps": 30, "_words": talk}
    assert any("not a graphic this style uses" in f for f in checks(bad, head, sty)[0]), "a kind outside the style must fail"
    short = {"graphics": [dict(phr, end=phr["start"] + phr["lines"][1]["words"][-1]["at"] + 0.5)], "zooms": [],
             "durationInFrames": 3000, "fps": 30, "_words": talk}
    assert any("too short to read" in f for f in checks(short, head, {})[0]), "a phrase gone as its last word lands must fail"
    # zooms and sound cues follow the style: sdr-mastery punches 4.9 a minute at 1.15x from a 41% face
    assert zoom_gap({"zoom": {"per_min": 2.8}}) == ZOOM_MIN_GAP_S and zoom_gap({"zoom": {"per_min": 4.9}}) == 4.0
    assert zoom_scale({"cx": 0.5, "top": 0.15, "h": 0.6, "bottom": 0.75}, 0.407, 1.15) == 1.15
    cards = [{"kind": "list", "start": float(t), "end": t + 5.0} for t in (5, 20, 40, 55, 120, 300, 500, 700, 900)]
    got = pick_sfx(cards, 600, {"per_min": 0.6, "on": ["list"], "opening": 4})
    assert len(got) == 6 and sum(g["start"] < 60 for g, _ in got) == 4, got   # 4 in the opening, the rest spread
    assert len(pick_sfx([{"kind": "chapter", "start": 9.0, "end": 12.0}], 600)) == 1, "axis-story's cues unchanged"

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
