# Handoff: cold-calling-one

## Update 2026-10-13 afternoon: fix cycle after join_audit (cut ready for Ayush to watch)

Pushed e65b58c (join_audit.py, verify engine from .meta.json, cut approved by watching). Ran `join_audit.py` on the
previous cut (12 of 195 joins flagged), fixed, rebuilt (`--max-pause 0.3`), rendered, `verify_cut.py` (engine from
meta: whisper small), `join_audit.py` again, `preview_cut.py`. One cycle, as asked.

**Current cut.mp4**: 42,051 frames, 23:21.7, built from `decisions.json` of this cycle. Verify: 98.8% match.
join_audit: 9 of 196 joins flagged (`joins.json`, `join_audit.log`).

Fixed this cycle:
- Cut-script rule `edge_scraps` (committed f41f157, tested): a scrap at a join is either a phrase's first word said
  before its label (put back whole: "A lot of people" at 5:48) or a mouth click (removed). `quiet_edges`: a removed
  word heard before its label is not taken for the kept word's tail.
- Span: the first "that" in "the worst thing that, that can happen" (now "...thing that can happen").
- Fragments at 8:01, 8:34 and 16:53 (mouth clicks) are gone.

Not changed, on purpose:
- 3:46 "a volume" CLIPPED and 5:49 "them" CLIPPED: false alarms. The audio says the intended "it's a volume game"
  and "a lot of people, they'll call someone": the raw transcript muddled the takes, so the expected words are off.
- 10:17 and 22:45 "and" SURVIVED: real, natural words ("calling earlier, and that leads into lesson six"); the
  printed spans ("and that", "and you") would also delete the next word.
- 8:56 "how how": he says "if you know how... how other customers"; "know how" is one sound and the transcript
  stretches "other" over the pause, so no span cuts the first "how" cleanly (tried "how" and "if you know how":
  both left it or cut 0.9 s into the second one). Needs a cut point from the audio.
- The other stutters (I, I ran; at, at least; more, more; contract to SDR): each a blur the transcript lumps
  into one word; a span would clip the word that stays.

**Regressions this cycle (fix in the cut scripts):** the click rule took two short words for clicks:
- 1:25.1 "makes sense or not || problem is": **"the"** removed (heard 3 of 3). Its sound (60 ms, peak -34 dB at
  source 109.22) sits right before "problem", 4 s after its label.
- 17:55.8 "before I call || before that": **"them"** removed (2 of 3); source ~1429.44, 60 ms, peak -26 dB.
  Real clicks here were 40-60 ms at -31 to -35 dB: length and level do not separate them from "the"/"them".
  Suggest: only remove a scrap as a click when no word label (fitted) lies within 0.5 s of it, or never at a kept
  START.

**Joins worth a listen in cut.mp4** (given to Ayush):

| Time | Words either side | What may be wrong |
|---|---|---|
| 1:25 | "makes sense or not \|\| problem is what happens" | "the" lost (regression) |
| 2:50 | "based on the volume. \|\| Now, typically" | verify heard "now now" |
| 5:48 | "then I break it up \|\| A lot of people..." | a short sound heard as "um" |
| 8:56 | "if you know how \|\| how other customers" | "how how" doubled |
| 14:03 | "I just hung up, but \|\| I was terrified" | "but" mumbled, heard as "I didn't" |
| 17:55 | "before I call them \|\| Before that" | "them" lost (regression) |
| 21:23 | "for quite a while. \|\| This is super consistent" | heard "this this", "is" clipped |

## Earlier state (before this update)


SDR Mastery, video 1 of 2: "If you only watch one cold calling video, make it this."
Source: `/Users/ayushbuche/Downloads/If You Only Watch One Cold Calling Video Make It This.mp4` (30:39, 1920x1080, 30 fps).
Style: `styles/sdr-mastery/` (approved). Paused so the cut scripts can be improved in another session.

## Where the edit is

Long-form skill **step 1 (cut), waiting on Ayush's approval of the cut**. Steps 2-3 are prepared but not run.

| File | State |
|---|---|
| `spans.json` | 31 cuts: 19 mistakes + 12 `redundant` (the tighten-to-~23-min pass Ayush agreed to) |
| `decisions.json`, `report.json`, `words.json` | Built 2026-10-13 ~11:45 with `--max-pause 0.3` and every cut-script fix below. 196 kept spans, **23:21.6** |
| `cut.mp4` | Matches `decisions.json` (42,049 frames). Video from `render.py`; audio rebuilt by hand with the new two-track crossfade (same code `render.py` now uses), because the old crossfade chain was too slow |
| `cut-check.html` | **Stale**: from an earlier build. Re-run `preview_cut.py` |
| `verify.log`, `cut.transcript.json`, `heard.json` | **Stale**: from the build before the last one (before the "voiced sounds are never cut as breath" fix). `verify_cut.py` has **not** run on the current `cut.mp4` |
| `board.json` | 36 graphics, passes the plan checks against the build before the last. Re-check against the current `words.json` (times moved) |
| `images/` | 4 illustrations made for this video (Higgsfield, gpt_image_2_5, 1 credit): bad-call, commute, hang-up, gym |
| `audio/track.mp3` | "Curiosity" by Diego Nava, Mixkit free licence, **no credit needed** (`audio/MUSIC-LICENSE.md`) |

Since the last full render: rebuilt `decisions.json` (voiced-run fix), rendered video, rebuilt the audio with the
new crossfade, joined them. Checked: frames 42049 of 42049, audio 1401.633 s = kept 1401.633 s; at 195 joins, 2 dips
and 1 click (below). Not re-verified by a second transcription.

## Transcription engines

- `words.raw.json`: **Whisper small** (CPU, int8) through `transcribe.py`, engine `whisper`. No TypeSafe or
  ElevenLabs key, so `retakes.py propose` judged nothing; Claude wrote `spans.json` from `transcript.txt`.
- `verify_cut.py`: `--engine whisper` (the same small model).

## Ayush's notes on this edit, in his words, and what was done

| # | Note | Done? |
|---|---|---|
| 1 | "I want to recreate the same style exactly the same and see if we can do that for the next video." | Done: `styles/sdr-mastery/` measured from the reference and approved |
| 2 | Copy it exactly (stock images, screenshots, the client's own footage allowed for this style) | Done: BUILD-BRIEF.md "Second style" |
| 3 | "The salesperson was used in this example, but that might be specific to the video ... For each video, it should be relative and specific to that video." | Done: 4 illustrations made for this video; rule in longform `references/graphics.md` |
| 4 | "I don't want to use any tracks where I have to put the credit in the description. I just want to use tracks that don't need any credit. And that are free to use." | Done: Mixkit track; rule in BUILD-BRIEF.md and the longform skill |
| 5 | "The BANT only works if we're explaining a framework ... make sure you're using graphics and text to help with understanding and not just to be flashy." | Done: rule in `references/graphics.md`; the board uses no acronym card (none is spelled out) |
| 6 | "If you think it's better to tighten it to 23 minutes, then let's do that ... but what's the reason for it?" | Done: 12 `redundant` cuts, pitch at ~15:20 trimmed, 27:11 -> 23:22 |
| 7 | "I haven't looked at it yet. I will look at it when the video is done too." | Noted (memory): he reviews by watching, not the struck-through page |
| 8 | "It doesn't look like a lot of the silences are cut out ... make sure none of the words are cut off ... the ending of the words cut off. I think we had that issue with the last video ... relatively fast-paced ... especially during the intro." | Mostly done (cut-script fixes 1-4, 6 below). Sentence gaps now median 0.25 s, 222 wpm (reference 0.26 s, 218). Residual issues listed below |
| 9 | "If you're not sure, then it might be best for me to check because I want to keep in mind credit usage, and I want to make this as good as possible." | Partly: checks run (re-listen, level at every join); the 3-minute sample was prepared but Ayush then said to skip it |
| 10 | "At 49 seconds, the word 'meetings' is cut off ... you need to keep stuff like that in mind." | Done: "s" kept to 53.23 s in the source (fix 5) |
| 11 | "If he takes in a breath between words or sentences, not just a normal quick one, then that can get cut too ... still make sure it sounds natural." | Done for the breath before a sentence (fix 6). Not re-verified by ear or by `verify_cut` on the current cut |
| 12 | "At 2:48, there's a little bit of a weird, harsh cut where he says 'teams that I worked at' ... make sure we don't have any of those anywhere else." | Done at 2:48 (cut moved to real pauses: "...top of the leaderboards. The top three..."); every join now crossfades. Other one-breath joins remain (below) |
| 13 | "Make sure that we don't have loads of gaps. A lot of the breathing gaps, we don't want them ... as fast-paced as possible without sounding rushed." | Partly: as 8 and 11. Gap of 0.2 s kept after a sentence + 0.1 s before the next |
| 14 | "If it takes minutes, just finish the new version ... I still want the quality and good quality results with this faster method." | Done: faster crossfade, exact length, joins checked |

## Cut-script fixes made during this edit (all committed, with tests)

1. `derive_noise_db`: the room floor is looked for among the quietest 15% of the take. A non-stop talker's clean
   take had been read as one over a **music bed** (floor -26 instead of -65), so pauses stayed in and splices
   followed word labels (clipped endings).
2. `quiet_edges`: no kept audio starts or stops while the voice is sounding, judged by whose sound it is (a kept
   word ringing on past its label vs a removed word already begun).
3. Onset walk-back in `splice_neighbours` capped at 0.25 s: it walked through removed words said in one breath
   and brought them back ("that's what I do at SDR Master." 1.3 s back in a cut pitch).
4. Settled tails round **up** to the next frame.
5. Hiss track (`HISS_AF`): a word's final "s" is quiet overall but loud in the hiss; a breath has none. Keeps the
   "s" after a closure ("meetings").
6. `breath_end`: the in-breath before a sentence is cut, keeping `PRE_ONSET_S` 0.1 s before the first voiced sound.
7. `voiced_runs`: a pause cut never takes a voiced sound (a soft "and" after a tiny gap had been cut as a breath).
8. `render.py`: 24 ms crossfade at every join (was fade-to-nothing, which made one-breath joins harsh), built as two
   overlapping tracks summed in one pass.
9. Long-form skill: always `--max-pause 0.3` (the taste file's `cut.max_pause` 0.1 is a Shorts setting).

## Known or suspected mistakes in the current cut.mp4

Times are in `cut.mp4`. "Suspected" ones come from word labels or the level at the join and need ears or a fresh
`verify_cut` to confirm: labels drift 0.1-0.5 s, so some are false alarms.

| Time | Words around it | Problem |
|---|---|---|
| 5:39.2 | "I call every \|\| er, single... contact a minimum of seven times" | Suspected: part of the stumble (an "er", one "every/single") may survive; voice sounding across the join (+23 dB) |
| 5:49.1 | "A lot of people, them, they'll call someone seven times" | Likely: "them" (from the cut "they'll Put them,") survives; a 24 dB dip at the join |
| 7:34.0 | "different clients across \|\| So. many different industries" | Suspected: "So." from the cut "Cross. So." may survive; one-breath join |
| 10:30.7 | "my company didn't tell me this, \|\| you can look it up" | Previous re-listen heard a fragment ("that") of the cut "but the highest," at this join |
| 12:31.2 | "time to stay consistent. \|\| that's what I do at SDR Master." | One-breath join (+23 dB): check it is not harsh |
| 13:04.9 | "They were in the hardware space. \|\| industries so there's a link" | Suspected: "industries" from the cut line survives |
| 15:50.8 | "you're more comfortable. You \|\| When that leads to lesson number eight" | "You When" was to be cut; label check says "When" (and maybe "You") survive |
| 20:30.3 | "I give up. \|\| But the thing that's going to determine" | A small click at the join |
| 21:23.5 | "quite a while. \|\| is, this is super consistent" | Suspected: "is," survives from the cut "And this is," |

From the previous re-listen (one build earlier; times may be ~2 s off), real stutters left in, not cut: "I, I ran a
podcast" (~1:57), "the worst thing that, that can happen" (~2:14), "meetings start until at, at least 10 a.m."
(~11:35), "a contract to SDR" (~14:55), "deals which will more, more than pay for" (~21:37). Their suggested spans
are in `verify.log`.

## Tried and did not work

- **A chain of 196 `acrossfade` filters** in one ffmpeg graph: correct, but ran about 5x slower than real time
  (over an hour for this cut). Replaced by two tracks summed with `amix`.
- **First `quiet_edges` (audio only)**: moved edges by sound alone, so it cut "comfortable" (its label ended 0.6 s
  early) and put back "You When". Rewritten to take the kept and removed words into account.
- **The first join checker** flagged any join where the removed side was loud; only sound carried across the join
  matters.
- **Telling an "s" from a breath by level**: the "s" of "meetings" is only 5 dB over the threshold, about a
  breath's level. Needed the hiss track.
- **Lists of "words kept / lost" from word labels**: mostly noise (labels drift). Use `verify_cut.py` and the level
  at each join.
- A test that measured against the constant it was testing (passed with the fix switched off); fixed.

## Decision to ask Ayush about (not changed)

BUILD-BRIEF.md "Mode" says the one approval is "the cut, shown as a transcript with removals struck through (text,
no rendering)". On this edit Ayush reviewed the cut by **watching** it, said he will judge "when the video is done",
and also asked to check a sample when the cuts are uncertain. Should the approval become a rendered cut (or its
first minutes) instead of the struck-through page?

## Left before Ayush can approve the cut

1. In the other session: whatever the cut scripts change, rebuild with
   `build_timeline.py <source> edits/cold-calling-one --max-pause 0.3`, then `render.py`.
2. Fix the mistakes above (span edits for the stumbles at 5:39, 5:49, 7:34, 13:04, 15:50, 21:23; move one-breath
   edges to real pauses as at 2:48).
3. `verify_cut.py edits/cold-calling-one --engine whisper` on the new `cut.mp4`, and the join check (level dips and
   clicks at each join), then `preview_cut.py` to refresh `cut-check.html`.
4. Ayush listens (he reviews by watching). Then: `face.py`, re-check `board.json` against the new `words.json`,
   `longplan.py edits/cold-calling-one --style styles/sdr-mastery/style.json --music audio/track.mp3`, `edit.py render`.
