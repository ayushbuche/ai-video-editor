# What goes on screen

The board (`edits/<name>/board.json`) is where an edit is won or lost. These are the rules, from the
references (`styles/axis-story/teardown.md`) and from Ayush's notes on the first test edit (2026-10-10).

## When a graphic earns its place

A graphic goes up only where it makes what he says **easier to understand**: a concept, a framework, a
process, a before/after, a number worth seeing, a script he reads out, a thing he names (his episode, a
tool). Never to fill time, never to reach a share of screen time, and never over a sentence that is
understood perfectly well from the speaker. Long stretches with no graphic are fine.

Before adding one, ask: would a viewer understand this line better with it? If not, leave the speaker.

## Which kind

The kinds below are axis-story's. **Each style lists its own kinds** (`style.json` design.kinds) and the
plan fails a kind the style does not use. sdr-mastery's are in the next table.

| He is... | Use | Not |
|---|---|---|
| explaining a framework, steps, a process, a model | `panel` with a `diagram` (flow, letters, list, pyramid, mindmap, compare, swoosh) | white words |
| telling how something grew or progressed | `panel` + `swoosh` | |
| saying the line the whole video turns on | `quote` (his exact words, key phrase in `**bold**`) | |
| reading a script, or quoting what someone said to him | `script` (the whole script, heading above it) | white words, quote |
| naming his own episode, video or product | `panel` with `image` + `"fit": "frame"` | a text label |
| listing 2-3 short items in passing | `buttons` (red pills over the speaker) | a screen of its own |
| landing a short punchy phrase or number that needs no explaining | `lower` (the white spoken words) | anything longer |
| starting numbered part N of a video built in parts | `chapter` | a video with no numbered parts |

The white spoken words (`lower`) are a visual beat, not an explanation: a few words ("$100M SaaS
company", "Always ask permission first"). Never a process with arrows, a list, or a script.

### sdr-mastery (white pages, red accent; `styles/sdr-mastery/teardown.md`)

| He is... | Use |
|---|---|
| giving the video's roadmap ("three parts"), and again at the start of each part | `rows` with `preview`: Part 1/2/3 labels, a part's text blurred until he names it |
| giving a few steps, things to do, options | `list` (heading on the red underline, numbered or red dots, lines arrive as said) |
| stating a number or a split ("1% of my calls / converted to a meeting") | `rows` (each row arrives when said) |
| reading a call script, or what a prospect says and what he answers | `dialogue` (one turn per speaker, the whole exchange stays) |
| stating his one rule or the point of something | `rule` (italic header on the highlighter, one line, on a card) |
| spelling out an acronym | `acronym` (one word per letter, each on the word) |
| describing a scene, a person or a situation (calls, a rep at a desk) | `illustration`: one made for this video (below) |
| naming a tool, a site or a product | `shot` (a real screenshot, full frame or framed) |
| landing a short punchy line (a few words) | `phrase` (bold sans line + italic serif line on a red underline, over him) |
| recapping the parts at the close | `list` with `"card": true`, red dots, no heading |

**Illustrations are made for each video** (Ayush, 2026-10-13): the reference's navy line-art look (one
character style, navy and pale blue on white, clean ink lines) with a subject drawn from what he says
there. Never reuse the reference's salesperson for its own sake. Put them in `edits/<name>/images/`.

The reference opens on the client's own footage for the first seconds, puts graphics up for about half
of the first minute, then thins out: under 10% after minute 11 (the plan prints the share). Stock photos
and third-party screenshots are allowed in this style (Ayush, 2026-10-13: copy it exactly).

## Timing and readability

- Every time is a quote of his words; elements arrive on the word that names them.
- **Never a graphic over silence.** The plan fails one with no talking under it.
- **Long enough to read.** Once all of a graphic is up and settled, it stays at least 2 s, plus 0.3 s a
  word. The planner brings items in earlier to make room (from the start of the sentence); if there is
  still not enough time, it fails: start it earlier in the sentence (`from`), or leave it out.
- Scripts build as he says them: each sentence starts coming in 0.6 s before he says it and stays.
- Graphics closer than 1 s join, so the speaker never flashes up for a moment between two.
- sdr-mastery's pages bring every word in as it is said, so the eye reads along: they need only stay 2 s
  after the last word lands.

## Motion

Smooth everywhere: soft, long ease-outs, no snap and no overshoot. Things fade in from a slight blur;
overlays on the speaker ease out over 0.5 s after the last word, never cut off. Items keep their places as
they arrive (a row or a line never re-centres). Changes between full layouts (speaker, panel, quote,
script page) are hard cuts, as in the references.

## Never

- Captions (the references have none).
- Stock footage, or photos of real people other than the client's own content (axis-story; sdr-mastery
  copies its reference, which uses both).
- Anything over the face: overlays sit under the chin (the plan fails one that cannot).
- A graphic the speaker card would cover (diagrams stay left of x 1190 on the panel).
