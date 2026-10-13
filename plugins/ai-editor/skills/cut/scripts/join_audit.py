#!/usr/bin/env python3
"""Listen to every join of a cut on its own: what a whole-file transcript smooths over.

    python3 join_audit.py <edit_dir> [--win 1.4] [--joins 40-80]   with the venv python ($PY: it needs faster-whisper)
    python3 join_audit.py demo                         self-check (offline, no model)

verify_cut.py transcribes the whole cut in one pass, and a whole-file transcriber tidies speech: a doubled
"that, that" comes back as one "that", half a word comes back as the whole word, and a 0.1 s blob of the
next take's first word comes back as nothing. All three sit on a join. This transcribes a short window round
every join ON ITS OWN (local Whisper, the model the raw transcript used, no voice detection, nothing carried
over from the window before) and reads the level there. A join with a heard flag is heard twice more, with a
shorter and a longer window; only flags two of the three listens agree on are reported as worth a listen
(on the first long-form edit, about half the single-listen flags were the window mishearing). It flags:

  DOUBLED    the window says a word or two-word phrase twice in a row where the intended cut does not
  SURVIVED   a word heard at the join that the cut removed (part of a take that was meant to go)
  CLIPPED    a kept word within 0.3 s of the join that the window does not hear
  FRAGMENT   a sound under 0.18 s right at the join, quiet on both sides, with no kept word on it: the start
             or end of a removed word, which no transcriber prints

Each flag gives its time in the cut and in the source and the words round the join; DOUBLED and SURVIVED
also give the spans.json entry to add if it is real. A flag is a place to listen, not a verdict: Whisper
mishears a short window too, so a flag with clean words either side is often nothing.

Reads   <edit_dir>/cut.mp4, decisions.json, words.raw.json (+ report.json's fitted labels)
Writes  <edit_dir>/joins.json   every join: its times, the words either side, what was heard, its flags
Exit 0 no flags, 1 flags, 2 usage or a missing file
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_timeline import RMS_WIN_S, derive_noise_db, is_kept, load_fitted, retime  # noqa: E402
from textnorm import canon, norm, pair_by_time, timed_words  # noqa: E402
from verify_cut import FILLERS, span_to_add, to_source  # noqa: E402

SR = 16000
WIN_S = 1.4            # each side of the join (Albert's reel editor: 1.4 s caught every doubled join it met)
EDGE_S = 0.2           # words this close to a window edge are half-heard: ignored on both sides
CLIP_NEAR_S = 0.3      # a kept word this close to the join that the window misses is CLIPPED
NEAR_REMOVED_S = 4.0   # removed words within this of the join (source seconds) are what may have survived
FRAG_MAX_S = 0.18      # a sound shorter than this at the join is a FRAGMENT (a word is longer)
FRAG_TOUCH_S = 0.03    # ...if it starts or ends this close to the join
FRAG_LOOK_S = 0.4      # how far either side of the join to look for sounds
FRAG_DB = 6.0          # a window this far over the silence threshold is sound (build_timeline.EDGE_DB)
FRAG_QUIET_WINDOWS = 2 # ...quiet for at least this many windows (40 ms) on both sides
RELISTEN = (0.7, 1.5)  # each heard flag is heard again in windows this much shorter and longer, centred on it


# ---------------------------------------------------------------- the judgements (pure, tested in demo)

def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def tokens(words):
    """[(token, start, end)] from word dicts, canonical (textnorm), fillers kept."""
    return timed_words([dict(w, type="word") for w in words])


def repeats(toks):
    """Indices i where toks says a word or a two-word phrase twice in a row: [(i, n)] (n = 1 or 2)."""
    out = []
    for i in range(len(toks)):
        if i + 1 < len(toks) and toks[i] == toks[i + 1] and toks[i] not in FILLERS:
            out.append((i, 1))
        elif i + 3 < len(toks) and toks[i:i + 2] == toks[i + 2:i + 4] and not set(toks[i:i + 2]) <= FILLERS:
            out.append((i, 2))
    return out


def fragment_of(removed):
    """A test: is a heard token one of these removed words, or the start or end of one ("betyd" of "betyder")?"""
    rem = set(removed)

    def test(tok):
        return tok in rem or any(len(tok) >= 2 and len(r) >= 2 and (r.startswith(tok) or tok.startswith(r))
                                 for r in rem)
    return test


def judge(t, exp, heard, removed):
    """Flags for one join at cut time t. exp, heard: [(token, start, end)] on the cut's timeline inside the
    window (what the cut meant to play, what the window heard). removed: canonical tokens the cut removed near
    this join. Returns [{"kind", "text", "start", "end"}]."""
    flags = []
    e_toks, h_toks = [x[0] for x in exp], [x[0] for x in heard]
    same, differ, gone, new = pair_by_time(exp, heard)
    meant = {" ".join(e_toks[i:i + 2 * n]) for i, n in repeats(e_toks)}
    for i, n in repeats(h_toks):
        said = " ".join(h_toks[i:i + 2 * n])
        if said not in meant:
            flags.append({"kind": "DOUBLED", "text": said, "start": heard[i][1], "end": heard[i + 2 * n - 1][2]})
    is_removed = fragment_of(removed)
    doubled = {k for f in flags for k in range(len(heard)) if f["start"] <= heard[k][1] <= f["end"]}
    for j in sorted(new):
        tok = h_toks[j]
        if tok not in FILLERS and is_removed(tok) and j not in doubled:
            flags.append({"kind": "SURVIVED", "text": tok, "start": heard[j][1], "end": heard[j][2]})
    for i in sorted(gone):
        tok, a, b = exp[i]
        if tok not in FILLERS and a <= t + CLIP_NEAR_S and b >= t - CLIP_NEAR_S:
            flags.append({"kind": "CLIPPED", "text": tok, "start": a, "end": b})
    return flags


def strong_flag(f):
    """A flag worth a listen: a FRAGMENT (measured, not heard), or a heard flag at least two listens agree on."""
    return f["kind"] == "FRAGMENT" or f.get("heard_in", 1) >= 2


def fragments(lvl, noise_db, t, kept):
    """Short sounds right at the join with no kept word on them. lvl: dB per RMS_WIN_S window of the cut.
    kept: [(start, end)] of the kept words on the cut's timeline. Returns [{"kind", "start", "end"}]."""
    if noise_db is None:
        return []
    thr = noise_db + FRAG_DB
    lo = max(0, int((t - FRAG_LOOK_S) / RMS_WIN_S))
    hi = min(len(lvl), int((t + FRAG_LOOK_S) / RMS_WIN_S) + 1)
    runs, k = [], lo
    while k < hi:
        if lvl[k] > thr:
            j = k
            while j < len(lvl) and lvl[j] > thr:
                j += 1
            runs.append((k, j))
            k = j
        else:
            k += 1
    out = []
    for a, b in runs:
        s, e = a * RMS_WIN_S, b * RMS_WIN_S
        if e - s >= FRAG_MAX_S or not (s - FRAG_TOUCH_S <= t <= e + FRAG_TOUCH_S):
            continue
        quiet_before = all(v <= thr for v in lvl[max(0, a - FRAG_QUIET_WINDOWS):a]) and a >= FRAG_QUIET_WINDOWS
        quiet_after = all(v <= thr for v in lvl[b:b + FRAG_QUIET_WINDOWS]) and b + FRAG_QUIET_WINDOWS <= len(lvl)
        if not (quiet_before and quiet_after):
            continue
        if any(min(e, ke) - max(s, ks) >= 0.5 * (e - s) for ks, ke in kept):
            continue   # a short kept word ("a", "I") sitting on the join
        out.append({"kind": "FRAGMENT", "text": "", "start": round(s, 3), "end": round(e, 3)})
    return out


# ---------------------------------------------------------------- the run

def joins_of(spans):
    """[(cut time, source end of the left span, source start of the right span)] for every join."""
    out, t = [], 0.0
    for k in range(len(spans) - 1):
        t += spans[k]["end"] - spans[k]["start"]
        out.append((round(t, 3), spans[k]["end"], spans[k + 1]["start"]))
    return out


def model_name(d):
    """The Whisper size the raw transcript used (words.raw.meta.json), so both passes hear alike."""
    meta = Path(d) / "words.raw.meta.json"
    if meta.exists():
        m = json.loads(meta.read_text())
        if m.get("engine") == "whisper" and m.get("model"):
            return m["model"]
    return os.environ.get("AI_EDITOR_WHISPER_MODEL", "small")


def load_audio(path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw[: len(raw) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0


def levels(audio):
    """build_timeline.window_rms_db on samples already in memory (same windows, same dB)."""
    import numpy as np
    n = int(SR * RMS_WIN_S)
    m = len(audio) // n
    if not m:
        return []
    ms = (audio[: m * n].reshape(m, n).astype(np.float64) ** 2).mean(axis=1)
    return [10 * float(np.log10(v)) if v > 0 else -120.0 for v in ms]


def main():
    if sys.argv[1:] == ["demo"]:
        return demo()
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir")
    ap.add_argument("--win", type=float, default=WIN_S, help="seconds each side of a join")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--joins", help="only these joins, e.g. 40-80 (1-based): writes joins-40-80.json")
    a = ap.parse_args()
    d = Path(a.edit_dir)
    for f in ("cut.mp4", "decisions.json", "words.raw.json"):
        if not (d / f).exists():
            print(f"ERROR: no {d / f}", file=sys.stderr)
            return 2

    spans = json.loads((d / "decisions.json").read_text())
    raw = [w for w in load_fitted(d) if w.get("type") == "word"]
    kept = retime(raw, spans)
    kept_toks = tokens(kept)
    removed_words = [w for w in raw if not is_kept(w, spans)]
    joins = joins_of(spans)

    sys.path.insert(0, str(HERE.parents[2] / "lib"))
    os.environ.setdefault("HF_HOME", str(Path(os.environ.get("AI_EDITOR_HOME", Path.home() / ".ai-video-editor")) / "models"))
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("ERROR: faster-whisper missing. Run this with python3 <plugin>/lib/ai_editor/run.py (the editor's venv).",
              file=sys.stderr)
        return 2
    from ai_editor import models
    from transcribe import FILLER_PROMPT
    name = model_name(d)
    model = WhisperModel(str(models.whisper(name, check=False) or name), device="cpu", compute_type="int8",
                         download_root=str(models.DIR))
    audio = load_audio(d / "cut.mp4")
    dur = len(audio) / SR
    lvl = levels(audio)
    noise_db, _ = derive_noise_db(lvl)
    print(f"{len(joins)} joins, each heard on its own (whisper {name}, {a.win:g} s either side)", flush=True)

    first, last = (map(int, a.joins.split("-")) if a.joins else (1, len(joins)))
    kept_spans = [(w["start"], w["end"]) for w in kept]

    def listen(t, src_l, src_r, win, centre=None):
        """(what the cut meant, what the window heard, the transcript flags) for the join at t, with a window of
        win seconds either side of centre (the join itself unless given)."""
        c = t if centre is None else centre
        lo, hi = max(0.0, c - win), min(dur, c + win)
        segs, _ = model.transcribe(audio[int(lo * SR):int(hi * SR)], language=a.lang, word_timestamps=True,
                                   initial_prompt=FILLER_PROMPT, beam_size=5, condition_on_previous_text=False,
                                   vad_filter=False)
        words = [{"text": w.word.strip(), "start": round(lo + w.start, 3), "end": round(lo + w.end, 3)}
                 for s in segs for w in (s.words or []) if w.word.strip()]
        inner = (lo + EDGE_S if lo > 0 else 0.0, hi - EDGE_S if hi < dur else dur)

        def inside(x):
            return inner[0] <= (x[1] + x[2]) / 2 <= inner[1]
        exp = [x for x in kept_toks if inside(x)]
        heard = [x for x in tokens(words) if inside(x)]
        removed = [x for w in removed_words if src_l - NEAR_REMOVED_S <= w["start"] <= src_r + NEAR_REMOVED_S
                   for x in canon(norm(w["text"]).split())]
        return exp, heard, judge(t, exp, heard, removed)

    results, flagged = [], 0
    for n, (t, src_l, src_r) in enumerate(joins, 1):
        if not first <= n <= last:
            continue
        exp, heard, flags = listen(t, src_l, src_r, a.win)
        # a short window mishears too: hear each flag twice more, in windows of other sizes centred on it
        # (so the shorter one still holds it), and count the listens that agree
        for f in flags:
            mid = (f["start"] + f["end"]) / 2
            again = [listen(t, src_l, src_r, a.win * k, centre=mid)[2] for k in RELISTEN]
            f["heard_in"] = 1 + sum(any(g["kind"] == f["kind"] and g["text"] == f["text"] for g in fl)
                                    for fl in again)
        flags += fragments(lvl, noise_db, t, kept_spans)
        before = " ".join(x[0] for x in exp if x[2] <= t + 0.05)[-60:]
        after = " ".join(x[0] for x in exp if x[2] > t + 0.05)[:60]
        for f in flags:
            f["source"] = to_source(f["start"], spans)
            if f["kind"] in ("DOUBLED", "SURVIVED"):
                f["span_to_add"] = span_to_add(raw, to_source(f["start"], spans), to_source(f["end"], spans))
        results.append({"join": n, "cut": t, "source": [src_l, src_r], "before": before, "after": after,
                        "heard": " ".join(x[0] for x in heard), "flags": flags})
        strong = [f for f in flags if strong_flag(f)]
        if strong:
            flagged += 1
            print(f"\n{mmss(t)} in the cut (source {mmss(src_l)} -> {mmss(src_r)})  ...{before[-40:]} || {after[:40]}...")
            print(f"  heard: {results[-1]['heard']}")
            for f in strong:
                what = f" {f['text']!r}" if f["text"] else ""
                times = f" (heard in {f['heard_in']} of {1 + len(RELISTEN)} listens)" if "heard_in" in f else ""
                print(f"  {f['kind']}{what} at {mmss(f['start'])}{times}")
                if f.get("span_to_add"):
                    print(f"    span to add, if it is real: {json.dumps(f['span_to_add'])}")
        elif n % 25 == 0:
            print(f"  {n}/{len(joins)}", flush=True)

    weak = [(r, f) for r in results for f in r["flags"] if not strong_flag(f)]
    if weak:
        print(f"\nHeard once only ({len(weak)}), most likely the window mishearing: "
              + ", ".join(f"{mmss(r['cut'])} {f['kind']} {f['text']!r}" for r, f in weak))
    out = d / (f"joins-{first}-{last}.json" if a.joins else "joins.json")
    out.write_text(json.dumps(results, indent=1))
    kinds = {}
    for r in results:
        for f in r["flags"]:
            if strong_flag(f):
                kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"\n{flagged} of {len(results)} joins flagged" + (": " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
                                                        if kinds else "") + f" -> {out}")
    print("Signal and transcript checks only: listen at each flagged time before changing the cut.")
    return 1 if flagged else 0


def demo():
    def tk(s, t0, step=0.3):
        return [(w, round(t0 + i * step, 2), round(t0 + i * step + 0.25, 2)) for i, w in enumerate(s.split())]

    # a clean join: nothing
    exp = tk("the top of the leaderboards the top three", 10.0)
    assert judge(11.5, exp, exp, ["teams", "that"]) == []
    # a doubled word across the join that the cut did not mean ("at, at least")
    exp = tk("start until at least 10 am", 20.0)
    heard = tk("start until at at least 10 am", 20.0, 0.257)
    f = judge(20.7, exp, heard, [])
    assert [x["kind"] for x in f] == ["DOUBLED"] and f[0]["text"] == "at at", f
    # a doubled word the speaker really said, kept on purpose: not a flag
    exp = tk("very very good", 5.0)
    assert judge(5.4, exp, exp, []) == []
    # a doubled two-word phrase
    heard = tk("model costs model costs are high", 30.0)
    f = judge(30.6, tk("model costs are high", 30.0, 0.45), heard, [])
    assert f and f[0]["kind"] == "DOUBLED" and f[0]["text"] == "model costs model costs", f
    # a removed word that survived at the join ("them" from the cut "they'll put them")
    exp = tk("a lot of people they'll call", 40.0)
    heard = tk("a lot of people them they'll call", 40.0, 0.26)
    f = judge(41.1, exp, heard, ["they'll", "put", "them"])
    assert [x["kind"] for x in f] == ["SURVIVED"] and f[0]["text"] == "them", f
    # half of a removed word ("betyd" of "betyder") counts as surviving
    assert fragment_of(["betyder"])("betyd") and not fragment_of(["betyder"])("b")
    # a kept word at the join that is not heard: clipped; one far from the join: transcriber noise
    exp = tk("the word meetings is cut off", 50.0)
    heard = [x for x in exp if x[0] != "meetings"]
    f = judge(50.7, exp, heard, [])
    assert [x["kind"] for x in f] == ["CLIPPED"] and f[0]["text"] == "meetings", f
    assert judge(52.5, exp, heard, []) == []
    # fragments: 0.1 s of sound right on the join, quiet round it, no kept word on it
    lvl = [-70.0] * 100
    for k in range(50, 55):           # 1.00-1.10 s
        lvl[k] = -30.0
    assert [x["kind"] for x in fragments(lvl, -60.0, 1.0, [])] == ["FRAGMENT"]
    assert fragments(lvl, -60.0, 1.0, [(0.98, 1.12)]) == []          # a kept "a" on the join
    assert fragments(lvl, -60.0, 1.5, []) == []                       # not at the join
    for k in range(55, 65):           # longer: a word, not a fragment
        lvl[k] = -30.0
    assert fragments(lvl, -60.0, 1.0, []) == []
    assert fragments(lvl, None, 1.0, []) == []
    # join times and levels
    assert joins_of([{"start": 1.0, "end": 3.0}, {"start": 5.0, "end": 6.5}, {"start": 7.0, "end": 8.0}]) == \
        [(2.0, 3.0, 5.0), (3.5, 6.5, 7.0)]
    try:
        import numpy as np
        a = np.zeros(SR, dtype=np.float32)
        a[: SR // 2] = 0.5
        lv = levels(a)
        assert len(lv) == 50 and abs(lv[0] - 10 * np.log10(0.25)) < 1e-6 and lv[-1] == -120.0
    except ImportError:
        pass
    assert mmss(339.2) == "5:39.2"
    assert strong_flag({"kind": "FRAGMENT"}) and strong_flag({"kind": "DOUBLED", "heard_in": 2})
    assert not strong_flag({"kind": "CLIPPED", "heard_in": 1})
    print("join_audit ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
