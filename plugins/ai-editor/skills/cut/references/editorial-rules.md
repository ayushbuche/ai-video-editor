# Editorial rules: generic defaults

These rules cut content that is not a mistake. They are riskier than removing retakes, so they are
off unless the user wants the video shorter. Every cut made under them uses `kind: "redundant"`,
and cut-check.html highlights it for the user.

## The bar

A cut that removes something the user wanted is far worse than a cut that leaves something in.
Leaving a line costs them a trim. Removing a good take can cost them the take, and they may not
notice it is gone. When unsure, keep it, or cut it with `confidence: "low"`.

## Rules

### 1. Subsumed line
Cut a complete line when the next line says the same thing better.

> "She got the job after three interviews." then "After three rounds of interviews, she got the
> offer." Keep the second.

Keep the first if it carries a detail the second drops.

### 2. Doubled discourse marker
"You see, you see", "So, so", "But, but": cut the doubling, even when both are fluent. This covers
connecting words only. Repeated content ("I know a man... I know a man") can be deliberate and
stays.

### 3. Restating the point after it lands
Once the point has landed, cut the sentences that only say it again.

### 4. Announce, then ask
"Let's start with what an API is." then "So, what is an API?" Cut the announcement, keep the
question. Keep whichever line does the job; cut the one that only points at it.

## Pauses are not only dead air

The pause target comes from `style.json` (`pace.max_pause_s`) or the default 0.30 s. Two cases
where a pause is doing work:

- **Before a number or a reveal.** A short beat before a figure lets it land. If the cut feels
  rushed there, rebuild with a higher `--max-pause`.
- **Inside a spoken list.** Very tight pauses between list items make them run together.

Very short function words ("so", "I", "you") right after a join need a little lead-in or they
get swallowed. `build_timeline.py` leaves that room automatically. `verify_cut.py` reports any that
went missing.

## Opening and closing

- Cut dead air before the first kept word and after the last. The script does this.
- A breath or sigh that opens a personal story can be part of the story. If the user asks for it
  back, keep it with no pause cut between it and the first word.

## How a cut must sound (Ayush, 2026-10-13, long-form)

Rules for every video, in his words, from the first SDR Mastery edit (`edits/cold-calling-one/HANDOFF.md`
has what was done about each):

- **No word is ever clipped.** "Make sure none of the words are cut off ... when you make a cut, the ending
  of the words cut off. I think we had that issue with the last video." That includes a word's final "s":
  "At 49 seconds, the word 'meetings' is cut off ... I think he says 'meetings', so you need to keep stuff
  like that in mind."
- **Silences and breaths go.** "When there are gaps and he doesn't speak constantly, and there are small gaps,
  they cut that silence out." "If he takes in a breath between words or sentences, not just a normal quick
  one, then that can get cut too ... but still make sure it sounds natural. Don't make it sound a bit weird."
  "A lot of the breathing gaps, we don't want them."
- **Fast, never rushed.** "The cut needs to be relatively fast-paced ... especially during the intro, because
  the intro needs to be fast-paced and get people hooked in." "As fast-paced as possible without sounding
  rushed. We want it to be natural." (Long-form: `--max-pause 0.3`, breath before a sentence cut, 0.1 s kept
  before its first voiced sound.)
- **No harsh joins.** "At 2:48, there's a little bit of a weird, harsh cut ... make sure we don't have any of
  those anywhere else." A restart said in one breath has no quiet to cut in: move the span's edges to real
  pauses (check the level between the words), even if that drops a short aside; every join is crossfaded.
- **Check before the long render when unsure.** "If you are sure that the cuts will look good ... then we can do
  that. If you're not sure, then it might be best for me to check."

How to check, learned the hard way: word labels drift 0.1-0.5 s from the audio, so a list of "words kept or
lost" built from labels is mostly noise. The re-listen (`verify_cut.py`) and the level at each join are what
to trust.
