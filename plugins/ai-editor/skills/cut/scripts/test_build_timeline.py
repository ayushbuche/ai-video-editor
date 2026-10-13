#!/usr/bin/env python3
"""Self-check for build_timeline.py. No ffmpeg, no fixtures, runs in milliseconds.

    python3 test_build_timeline.py
"""
import contextlib
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_timeline as B  # noqa: E402


def levels(speech_db, floor_db, n_speech=200, n_floor=800):
    return [speech_db + 0.4] * n_speech + [floor_db + 0.4] * n_floor


def test_derive():
    assert B.derive_noise_db(levels(-14, -64))[0] == -40.0      # quiet room: speech - 26
    assert B.derive_noise_db(levels(-21, -65))[0] == -47.0      # quieter speaker moves it
    noise, d = B.derive_noise_db(levels(-13, -28))              # music bed: quietest 10% + 1/3
    assert d["bed"] == -27.6 and noise == round(-27.6 + 14.6 / 3, 1), d
    noise, d = B.derive_noise_db(levels(-13, -28, n_speech=50, n_floor=4000))
    assert d["speech"] == -13 and d["bed"] == -27.6, d           # busy floor is not speech
    assert B.derive_noise_db(levels(-11, -38))[0] == -32.0      # never under floor + 6
    # a speaker who hardly stops: more windows inside his speech (spread -40..-14 dB) than in the room tone
    # (-65 dB). The floor is the room tone, so no music bed (cold-calling-one, 2026-10-13)
    talky = [-14.6 - (i % 27) for i in range(9000)] + [-21.6 - (i % 10) for i in range(20000)] + [-64.6] * 1700 \
        + [-55.6 - (i % 9) for i in range(1500)]
    noise, d = B.derive_noise_db(talky)
    assert "bed" not in d and d["floor"] == -65, d


def test_audible_end():
    lvl = [-20.0] * 10 + [-60.0] * 10
    assert abs(B.audible_end(lvl, -40.0, 0.34) - 0.20) < 1e-9
    assert B.audible_end(lvl, -40.0, 0.10) == 0.10
    assert B.audible_end([-60.0] * 10, -40.0, 0.10) is None


def splice(left, right, next_dur, budget=0.18):
    words = [{"start": 0.0, "end": 1.0, "text": "prev"}, {"start": 1.5, "end": 1.6, "text": "flub"},
             {"start": 3.0, "end": 3.0 + next_dur, "text": "next"}]
    cut = {"start": 1.0 + left, "end": 3.0 - right, "kind": "retake", "evidence": "flub",
           "confidence": "high"}
    B.enforce_splice_budget([cut], words, [{"start": 1.5, "end": 1.6}], budget)
    return (cut["start"] - 1.0) + (3.0 - cut["end"]), cut


def test_splice_budget():
    total, cut = splice(0.125, 0.125, 0.06)
    assert abs(total - 0.18) < 1e-6 and 3.0 - cut["end"] >= 0.125 - 1e-6, cut   # short word keeps runway
    assert abs(splice(0.10, 0.10, 0.30)[0] - 0.18) < 1e-6
    total, cut = splice(0.05, 0.05, 0.30)                                         # in budget: untouched
    assert abs(total - 0.10) < 1e-9 and abs(cut["start"] - 1.05) < 1e-9
    for left, right, nd in [(0.4, 0.4, 0.06), (0.02, 0.5, 0.30), (0.5, 0.02, 0.06)]:
        _, cut = splice(left, right, nd)                                          # only widens,
        assert cut["start"] <= 1.0 + left + 1e-9 and cut["end"] >= 3.0 - right - 1e-9
        assert cut["start"] > 1.0 and cut["end"] < 3.0                           # never into a word
    _, cut = splice(0.4, 1.0, 0.06, budget=0.001)
    assert 1.0 <= cut["start"] and cut["end"] <= 3.0


def test_spans():
    toks = [{"text": t, "start": i, "end": i + 0.5, "type": "word"}
            for i, t in enumerate("so the thing about the thing about ducks".split())]
    cuts = B.resolve_spans([{"text": "the thing about", "occurrence": 1, "kind": "false_start"}], toks)
    assert (cuts[0]["start"], cuts[0]["end"]) == (1, 3.5), cuts
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):  # the expected ERROR stays out of the CI log
            B.resolve_spans([{"text": "the thing about", "kind": "false_start"}], toks)
        raise AssertionError("an ambiguous span must fail")
    except SystemExit:
        assert "appears 2x" in err.getvalue(), err.getvalue()


def test_frames_and_retime():
    cuts = [{"start": 1.01, "end": 1.99, "_next": 2.0}, {"start": 3.0, "end": math.inf}]
    frames = B.kept_frames(cuts, 30, 4.0)
    assert frames == [[0, 30], [60, 90]], frames                 # floor start, clamp end
    spans = [{"start": s / 30, "end": e / 30} for s, e in frames]
    w = B.retime([{"text": "a", "start": 0.2, "end": 0.5, "type": "word"},
                  {"text": "gone", "start": 1.2, "end": 1.5, "type": "word"},
                  {"text": "b", "start": 2.1, "end": 2.4, "type": "word"}], spans)
    assert [x["text"] for x in w] == ["a", "b"] and abs(w[1]["start"] - 1.1) < 1e-6, w


def test_stretched_label_is_not_clipped():
    """Whisper labels "if" 0.4-3.4 s, 3 s ahead of its audio at 3.45 s (the sample take's "If" at
    173 s). Judged on that label, the pause cut "clips" a word the render plays, and the paper edit
    sends the model into raising --pad for nothing. Fitted to the audio, nothing is clipped and the
    paper edit plays exactly the words words.json keeps."""
    import preview_cut as P
    words = [{"text": "so", "start": 0.0, "end": 0.3, "type": "word"},
             {"text": "if", "start": 0.4, "end": 3.4, "type": "word"},
             {"text": "you", "start": 3.6, "end": 3.9, "type": "word"}]
    loud = [(0.0, 0.3), (3.45, 3.55), (3.6, 3.9)]
    lvl = [-20.0 if any(a <= i * B.RMS_WIN_S < b for a, b in loud) else -60.0 for i in range(int(4.5 / B.RMS_WIN_S))]

    def paper(ws):
        cuts = B.merge(B.silence_cuts(ws, 0.15, 0.1, [(0.3, 3.45)]) + B.lead_trail_cuts(ws, 4.5, 0.1))
        B.enforce_splice_budget(cuts, ws, [], 0.15, lvl, -40.0)
        spans = [{"start": a / 30, "end": b / 30} for a, b in B.kept_frames(cuts, 30, 4.5)]
        md = P.paper_edit(P.label(ws, [], spans), [], 4.5, sum(s["end"] - s["start"] for s in spans))
        return md, [w["text"] for w in B.retime(ws, spans)]

    assert "CLIPPED" in paper(words)[0]                       # the raw label: a false CLIPPED
    labels = B.fit_labels(words, lvl, -40.0)
    assert list(labels) == [1] and 3.4 <= labels[1][0] < labels[1][1] <= 3.6, labels
    md, kept = paper(B.apply_labels(words, labels))
    assert "CLIPPED" not in md and kept == ["so", "if", "you"], (md, kept)
    assert md.split("## What plays")[1].split("## Cuts")[0].split("\n")[-3] == "so if you", md



def test_hidden_repeat_is_listed_and_shown():
    """The sample: Whisper labels "content" 117.07-119.01 s over "and to break down competitor ads and"
    (spoken 117.7-119.4 s). A label holding far more speech than its word is listed, re-transcribed
    when possible, and otherwise marked in transcript.txt. A long label over silence is not listed."""
    import retakes as R
    import transcribe as T
    words = [{"text": "ads", "start": 116.6, "end": 117.0, "type": "word"},
             {"text": "content", "start": 117.07, "end": 119.01, "type": "word"},
             {"text": "strategies", "start": 119.5, "end": 120.0, "type": "word"},
             {"text": "if", "start": 121.0, "end": 124.0, "type": "word"}]   # 3 s label, 0.1 s of audio
    loud = [(116.6, 117.0), (117.7, 119.4), (119.5, 120.0), (123.9, 124.0)]
    lvl = [-20.0 if any(a <= i * B.RMS_WIN_S < b for a, b in loud) else -60.0 for i in range(int(125 / B.RMS_WIN_S))]
    assert [i for i, _ in B.unheard(words, lvl, -40.0)] == [1], B.unheard(words, lvl, -40.0)

    old = B.window_rms_db, B.derive_noise_db
    B.window_rms_db, B.derive_noise_db = (lambda src: lvl), (lambda lv: (-40.0, {}))
    try:
        asked = []
        def again(s, e):
            asked.append((s, e))
            return [{"text": x, "start": 117.7 + n * 0.2, "end": 117.85 + n * 0.2, "type": "word"}
                    for n, x in enumerate("and to break down competitor ads and content".split())]
        got = [w["text"] for w in T.recheck("a.wav", T.with_spacing([dict(w) for w in words]), again)
               if w["type"] == "word"]
        assert asked == [(117.07, 119.01)] and got[1:9] == "and to break down competitor ads and content".split(), got
        kept = [w for w in T.recheck("a.wav", T.with_spacing([dict(w) for w in words]), lambda s, e: [])
                if w["type"] == "word"]
        assert kept[1]["unheard_s"] > 1.0 and "unheard_s" not in kept[3], kept
        view = R.text_view(kept)
        assert "content [1.3s of speech not transcribed]" in view, view
        assert "not transcribed" not in R.say(kept, 0, 3)    # Jev's questions and spans see the plain words
        one = T.recheck("a.wav", T.with_spacing([dict(w) for w in words]),
                        lambda s, e: [{"text": "content", "start": 117.7, "end": 119.4, "type": "word"}])
        assert not any(w.get("unheard_s") for w in one), one    # heard again as one word: drawn out
    finally:
        B.window_rms_db, B.derive_noise_db = old


def _lvl(runs, total_s, speech=-20.0, floor=-70.0):
    """20 ms window levels: speech inside each (start, end) run, floor elsewhere."""
    n = int(total_s / B.RMS_WIN_S)
    return [speech if any(a <= i * B.RMS_WIN_S < b for a, b in runs) else floor for i in range(n)]


def test_label_ahead_of_its_word():
    # Whisper labels "Good" 2 s early, inside the pause; the word is said just before "deals"
    lvl = _lvl([(1.0, 1.8), (3.75, 5.0)], 6)
    toks = [{"text": "deals", "type": "word", "start": 1.3, "end": 1.8},
            {"text": "Good", "type": "word", "start": 1.83, "end": 2.87},
            {"text": "deals", "type": "word", "start": 3.96, "end": 4.3}]
    a, b = B.fit_labels(toks, lvl, -45)[1]
    assert 3.69 <= a <= 3.76 and b <= 3.96, (a, b)


def test_label_on_the_previous_words_tail():
    # "best, Now," with "Now" said 5 s later: the audio at the label's start is "best" ringing out
    lvl = _lvl([(0.5, 1.0), (6.08, 7.0)], 8)
    toks = [{"text": "best,", "type": "word", "start": 0.6, "end": 0.95},
            {"text": "Now,", "type": "word", "start": 0.95, "end": 1.97},
            {"text": "if", "type": "word", "start": 6.25, "end": 6.35}]
    a, b = B.fit_labels(toks, lvl, -45)[1]
    assert 6.0 <= a <= 6.1 and b <= 6.25, (a, b)


def test_cut_stops_where_the_removed_word_does():
    # "beautiful (pause) beautiful combination": the first is cut, its label ends 0.08 s before its sound
    lvl = _lvl([(0.76, 1.08), (1.66, 2.5)], 3)
    cut = [{"start": 0.56, "end": 1.0}]
    assert B.close_tails(cut, lvl, -45)[0]["end"] == 1.1
    # a fading tail that flickers around the threshold still ends the run
    lvl[int(1.08 / B.RMS_WIN_S) + 1] = -30
    assert 1.1 < B.close_tails(cut, lvl, -45)[0]["end"] <= 1.15
    # the onset of a kept word right after the cut is never taken
    lvl = _lvl([(0.2, 0.9), (1.0, 1.3)], 3)
    assert B.close_tails([{"start": 0.2, "end": 1.02}], lvl, -45)[0]["end"] == 1.02


def test_word_rings_out_before_a_pause_cut():
    # speech to 1.0 s, a soft tail 12 dB down to 1.14 s, silence to 2.0 s: the pause cut starts after the tail
    lvl = _lvl([(0.2, 1.0), (2.0, 2.6)], 3)
    for i in range(int(1.0 / B.RMS_WIN_S), int(1.14 / B.RMS_WIN_S)):
        lvl[i] = -52.0
    words = [{"text": "this", "start": 0.2, "end": 0.95}, {"text": "next", "start": 2.0, "end": 2.5}]
    c = B.silence_cuts(words, 0.3, 0.2, [(1.0, 2.0)], lvl, -45)[0]
    assert c["start"] >= 1.14, c
    assert B.release_end(lvl, -45, 1.0) >= 1.14


def test_mid_speech_removal_starts_in_the_dip():
    # "is," then "it's" with no pause: a dip to -48 at 0.70 s between them; the removal starts there
    lvl = _lvl([(0.2, 1.2)], 2, speech=-28)
    lvl[int(0.70 / B.RMS_WIN_S)] = -48
    assert abs(B.valley(lvl, -42, 0.86, 0.56) - 0.71) < 0.02
    assert B.valley(lvl, -42, 1.5, 1.4) == 1.5     # already silent: unchanged


def test_last_consonant_is_kept():
    # "market": the vowel fades under the threshold, a 40 ms stop, then the "t" burst; the cut waits for the burst
    lvl = _lvl([(0.2, 1.0)], 2, speech=-28)
    for k, v in enumerate([-46, -50, -35, -34, -48, -65]):
        lvl[int(1.0 / B.RMS_WIN_S) + k] = v
    assert B.release_end(lvl, -42, 1.0) >= 1.1
    # "response": a dip to -52 for 60 ms, then the "s" at -36 tailing off; the cut waits for the "s"
    lvl = _lvl([(0.2, 1.0)], 2, speech=-28)
    for k, v in enumerate([-52, -52, -42, -36, -37, -38, -40, -44, -50, -56, -61]):
        lvl[int(1.0 / B.RMS_WIN_S) + k] = v
    assert B.release_end(lvl, -42, 1.0) >= 1.18
    # a breath after a real 200 ms gap is not the word's: the cut goes in front of it
    lvl = _lvl([(0.2, 1.0), (1.2, 1.3)], 2, speech=-28)
    for k in range(10):
        lvl[int(1.0 / B.RMS_WIN_S) + k] = -60
    assert B.release_end(lvl, -42, 1.0) <= 1.2


def test_restart_in_one_breath_is_never_kept():
    # "is," dips to -48 for 20 ms, then "it's" at -23: a spoken word, so the removal starts in the dip
    lvl = _lvl([(0.2, 1.6)], 2, speech=-23)
    lvl[int(0.70 / B.RMS_WIN_S)] = -48
    assert B.voiced_rise(lvl, -42, 0.56, 1.2)
    # "response": the "s" after the dip peaks at -36, under voice level: the word's own ending
    lvl = _lvl([(0.2, 1.0)], 2, speech=-28)
    for k, v in enumerate([-52, -52, -42, -36, -37, -38, -40, -44, -50, -56, -61]):
        lvl[int(1.0 / B.RMS_WIN_S) + k] = v
    assert not B.voiced_rise(lvl, -42, 1.0, 1.3)


def test_quiet_edges():
    """No kept audio starts or stops while the voice is sounding, judged by whose sound it is (cold-calling-one,
    2026-10-13)."""
    q, v = -60.0, -20.0
    win = lambda spans, n=200: [v if any(a <= i * B.RMS_WIN_S < b for a, b in spans) else q for i in range(n)]  # noqa: E731
    w = lambda t, a, b: {"text": t, "start": a, "end": b}  # noqa: E731
    # "comfortable." labelled to 0.9 but sounding to 1.3: the cut placed on its label waits for it to die
    c = B.quiet_edges([{"start": 0.9, "end": 2.5}], win([(0.5, 1.3), (2.6, 3.5)]), -40.0, 4.0,
                      kept=[w("comfortable.", 0.5, 0.9), w("next", 2.6, 3.0)])
    assert 1.28 <= c[0]["start"] <= 1.34 and c[0].get("_settled"), c
    # ...but never into a removed word said straight after it (a restart in one breath): the edge stays
    c = B.quiet_edges([{"start": 0.9, "end": 2.5}], win([(0.5, 2.0), (2.6, 3.5)]), -40.0, 4.0,
                      kept=[w("at,", 0.5, 0.9), w("I", 2.6, 2.8)], removed=[w("and", 0.95, 1.2)])
    assert c[0]["start"] == 0.9, c
    # a removed "And" began at 0.76, after the kept word ended at 0.7: the cut moves back to the quiet before it
    c = B.quiet_edges([{"start": 0.8, "end": 1.6}], win([(0.3, 0.7), (0.76, 1.4), (1.7, 2.5)]), -40.0, 3.0,
                      kept=[w("meeting.", 0.3, 0.7), w("I", 1.7, 1.9)], removed=[w("And", 0.74, 0.9)])
    assert 0.7 <= c[0]["start"] <= 0.76, c
    # the kept audio began inside a removed "er" (0.6-0.78): it starts in the quiet after it
    c = B.quiet_edges([{"start": 0.2, "end": 0.74}], win([(0.0, 0.15), (0.6, 0.78), (0.86, 2.0)]), -40.0, 3.0,
                      kept=[w("call", 0.0, 0.15), w("every", 0.86, 1.1)], removed=[w("er,", 0.6, 0.62)])
    assert 0.78 <= c[0]["end"] <= 0.86, c
    # the kept audio began inside its own word's onset (from 1.96): it starts in the quiet before it
    c = B.quiet_edges([{"start": 1.2, "end": 2.02}], win([(0.5, 1.1), (1.96, 2.8)]), -40.0, 3.0,
                      kept=[w("a", 0.5, 1.1), w("b", 2.04, 2.8)])
    assert 1.9 <= c[0]["end"] <= 1.96, c
    # "thing that, that can": the removed first "that" sounds from 0.88, after a dip, 0.06 s before its label: the
    # cut moves back into the dip instead of keeping its first 60 ms
    c = B.quiet_edges([{"start": 0.94, "end": 1.12}], win([(0.4, 0.8), (0.88, 1.06), (1.16, 2.0)]), -40.0, 3.0,
                      kept=[w("thing", 0.4, 0.94), w("that", 1.12, 1.3)], removed=[w("that", 0.94, 1.12)])
    assert 0.8 <= c[0]["start"] <= 0.88, c
    # removed "You When" run straight into the kept "that": moving back would bring them in, so the edge stays
    c = B.quiet_edges([{"start": 0.5, "end": 1.94}], win([(0.1, 0.4), (1.78, 2.4)]), -40.0, 3.0,
                      kept=[w("x", 0.1, 0.4), w("that", 1.94, 2.12)], removed=[w("You", 1.58, 1.94), w("When", 1.94, 1.94)])
    assert c[0]["end"] == 1.94, c
    # a settled start is rounded UP to the next frame, so the frame never takes the tail back off
    assert B.kept_frames([{"start": 1.001, "end": 1.5, "_settled": True}], 30, 3.0)[0] == [0, 31]
    # an edge in silence, and a cut to the end of the take, are left alone
    c = B.quiet_edges([{"start": 1.2, "end": 1.8}], win([(0.5, 1.1), (1.96, 2.8)]), -40.0, 3.0)
    assert c == [{"start": 1.2, "end": 1.8}], c
    c = B.quiet_edges([{"start": 2.9, "end": math.inf}], win([(0.5, 1.1), (1.96, 2.8)]), -40.0, 3.0)
    assert c[0]["end"] == math.inf, c


def test_onset_walk_stops_at_removed_words():
    """A removed restart said in one breath with the kept words: finding the kept word's onset never walks back
    through the removed words (cold-calling-one, 2026-10-13)."""
    lvl = [-60.0] * 50 + [-20.0] * 150 + [-60.0] * 50          # one continuous sound 1.0-4.0 s
    cut = {"start": 1.0, "end": 3.0}                             # removes 1.0-3.0, said straight into the kept word
    kept = [{"text": "I", "start": 3.0, "end": 3.3}, {"text": "x", "start": 0.2, "end": 0.6}]
    _, nxt = B.splice_neighbours(cut, kept, lvl, -40.0)
    assert nxt["start"] >= 2.7, nxt                              # never back into the removed 1.0-3.0



def test_sibilant_and_breath():
    """The "s" after a closure stays with its word; the in-breath before the next sentence goes (2026-10-13)."""
    W = B.RMS_WIN_S
    lv = [-63.0] * 300
    for k in range(int(0.5 / W), int(0.92 / W)):
        lv[k] = -18.0                          # "meeting" to 0.92
    for k in range(int(1.0 / W), int(1.18 / W)):
        lv[k] = -30.0                          # its "s", after an 80 ms closure
    assert B.sibilant_end(lv, -41.0, 0.94, 5.0) >= 1.18
    # the real "meetings": its "s" only 5 dB over the threshold, but almost all hiss; a breath has no hiss
    lv2, hf = [-63.0] * 100, [-78.0] * 100
    for k in range(10, 46):
        lv2[k], hf[k] = -20.0, -60.0           # "meeting"
    for k in range(51, 60):
        lv2[k], hf[k] = -37.0, -40.0           # its "s" after a closure
    assert B.sibilant_end(lv2, -41.0, 0.94, 5.0) == 0.94                     # by level alone it is missed
    assert B.sibilant_end(lv2, -41.0, 0.94, 5.0, hf, -78.0) >= 1.2           # by its hiss it is kept
    for k in range(51, 60):
        lv2[k], hf[k] = -37.0, -77.0           # the same level with no hiss: a breath, not kept
    assert B.sibilant_end(lv2, -41.0, 0.94, 5.0, hf, -78.0) == 0.94
    for k in range(int(4.3 / W), int(4.7 / W)):
        lv[k] = -45.0 + 8                      # an in-breath at -37 (speech -15: 22 dB under)
    for k in range(int(4.75 / W), int(5.5 / W)):
        lv[k] = -15.0                          # "The funny thing"
    assert abs(B.breath_end(lv, -15.0, 4.3) - 4.74) < 0.03
    cuts = B.silence_cuts([{"text": "The", "start": 4.75, "end": 5.0}], 0.3, 0.2, [(0.94, 4.3)], lv, -41.0)
    assert cuts and cuts[0]["start"] >= 1.18 and 4.6 <= cuts[0]["end"] <= 4.66, cuts
    # a soft "and" (-31 dB, 10 over the threshold) after a tiny gap is a word, never cut as if it were a breath
    lv3 = [-63.0] * 200
    for k in range(10, 40):
        lv3[k] = -18.0                          # "months" to 0.8
    for k in range(44, 52):
        lv3[k] = -31.0                          # "and" 0.88-1.04
    for k in range(90, 150):
        lv3[k] = -16.0                          # "I work" from 1.8
    cuts = B.silence_cuts([{"text": "I", "start": 1.8, "end": 2.0}], 0.3, 0.2, [(0.8, 1.8)], lv3, -41.0)
    assert all(c["start"] >= 1.04 for c in cuts), cuts
    # no breath: the pause keeps its 0.1 s before the next word as before
    assert B.breath_end([-63.0] * 100 + [-15.0] * 50, -15.0, 2.0) == 2.0



def test_edge_scraps():
    """No join keeps a scrap of sound: a split first word goes whole to its phrase, a click goes (2026-10-13)."""
    W = B.RMS_WIN_S
    def lv(spans, n=250, base=-63.0):
        out = [base] * n
        for a, b, v in spans:
            for k in range(int(a / W), int(b / W)):
                out[k] = v
        return out
    # "up." to 1.0; "A" said at 1.30-1.44 (labelled later); "lot of people" from 1.62: the pause cut 1.38-1.58
    # split the "A". The cut now ends before it, so "A" plays whole
    c = B.edge_scraps([{"start": 1.38, "end": 1.58}], lv([(0.4, 1.0, -18), (1.3, 1.44, -18), (1.62, 2.4, -18)]), -41.0)
    assert c[0]["end"] <= 1.3 and c[0]["start"] < c[0]["end"], c
    # a click 0.4 s before the next words is still a click, not a word said early
    c = B.edge_scraps([{"start": 1.36, "end": 1.75}], lv([(0.4, 1.0, -18), (1.3, 1.34, -31), (1.78, 2.6, -18)]), -41.0)
    assert c[0]["start"] <= 1.3 and c[0]["end"] == 1.75, c
    # the split "A" whose first window ramps up (-38) after room tone: still found and kept whole
    c = B.edge_scraps([{"start": 1.42, "end": 1.6}], lv([(0.4, 1.0, -18), (1.3, 1.32, -38), (1.32, 1.4, -18),
                                                        (1.62, 2.4, -18)]), -41.0)
    assert c[0]["end"] <= 1.3, c
    # a click at 1.30-1.34 after "block." (to 1.0), the next words 2.0 s away: the kept audio stops before it
    c = B.edge_scraps([{"start": 1.36, "end": 3.0}], lv([(0.4, 1.0, -18), (1.3, 1.34, -30), (3.1, 4.0, -18)]), -41.0)
    assert c[0]["start"] <= 1.3, c
    # a click at 2.02-2.08, room tone, then "problem" from 2.14: the kept audio starts after the click
    c = B.edge_scraps([{"start": 1.2, "end": 2.0}], lv([(0.4, 1.0, -18), (2.02, 2.08, -34), (2.14, 3.0, -20)]), -41.0)
    assert 2.08 <= c[0]["end"] <= 2.12, c
    # a "p" burst then aspiration (well over room level) then the vowel: one sound, left alone
    c = B.edge_scraps([{"start": 1.2, "end": 2.0}], lv([(0.4, 1.0, -18), (2.02, 2.06, -30), (2.06, 2.12, -36),
                                                        (2.12, 3.0, -20)]), -41.0)
    assert c[0]["end"] == 2.0, c
    # a click right at the edge threshold (-35 dB, 6 over): still a click
    c = B.edge_scraps([{"start": 1.36, "end": 3.0}], lv([(0.4, 1.0, -18), (1.3, 1.34, -35), (3.1, 4.0, -18)]), -41.0)
    assert c[0]["start"] <= 1.3, c
    # a short word ("I", 120 ms, loud) alone before a pause and the next words: a word, not a click, so kept
    c = B.edge_scraps([{"start": 1.2, "end": 2.0}], lv([(0.4, 1.0, -18), (2.02, 2.14, -18), (2.22, 3.0, -20)]), -41.0)
    assert c[0]["end"] == 2.0, c


if __name__ == "__main__":
    test_derive()
    test_quiet_edges()
    test_edge_scraps()
    test_sibilant_and_breath()
    test_onset_walk_stops_at_removed_words()
    test_audible_end()
    test_splice_budget()
    test_spans()
    test_frames_and_retime()
    test_stretched_label_is_not_clipped()
    test_hidden_repeat_is_listed_and_shown()
    test_label_ahead_of_its_word()
    test_label_on_the_previous_words_tail()
    test_cut_stops_where_the_removed_word_does()
    test_word_rings_out_before_a_pause_cut()
    test_mid_speech_removal_starts_in_the_dip()
    test_last_consonant_is_kept()
    test_restart_in_one_breath_is_never_kept()
    print("all ok")
