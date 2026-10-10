# Style: axis-story

Measured from three references across their full length (40.9 minutes in total):

| Video | Length |
|---|---|
| [NEi32Vn302w](https://www.youtube.com/watch?v=NEi32Vn302w) | 9:26 |
| [az1Zh-FNSno](https://www.youtube.com/watch?v=az1Zh-FNSno) | 12:02 |
| [m_D2yOUapNQ](https://www.youtube.com/watch?v=m_D2yOUapNQ) | 19:25 |

All three are 1920x1080 at 25 fps. The numbers come from code (`style.json`, `timeline.json`).
The design notes come from full-resolution frames.

## Summary

A calm, teacherly explainer. **Graphics are on screen for over half the video (median 57%)**, and
most of that time is one layout: a light-grey rounded panel on the left with a hand-drawn marker
diagram that **builds stroke by stroke as he talks**, and the speaker in a rounded portrait card on
the right. Between graphics he is on camera for only a few seconds at a time. **No captions.** Sound
effects are rare. The look is cream, navy blue and red, with a serif for titles and a clean sans for
quotes.

## Pace over time

| | Value |
|---|---|
| Speech | 224 words a minute, pauses cut to 0.4 s or less |
| Cuts | 7.7 a minute on average (one every 3.8 s). The first minute is busiest (14-15 cuts); after that it settles to 3-11 a minute, with bursts of 20+ when graphics swap quickly. The last minute is near 0 (the end screen). |
| Zoom | Hard punch-ins (about 1.25x), 2.8 a minute, on cuts. The opening minute has 10-11 of them in two of the three videos, then 0-4 a minute. Slow push-ins are almost never used (0.1 a minute). |
| Transitions | Hard cuts 45%, punch-in 31%, jump 12%, whip 9%. Dissolves and other transitions about 1% each. |
| First graphic | About 6 s in (2-7 s). |
| Time on camera between graphics | Median 3.7 s. Longest stretch with no graphic: 13-27 s in two videos, 105 s once in the longest. |

**Attention resets** come from the layout changes, not from zooms: on camera → panel with
diagram → quote card → back on camera. A diagram panel usually stays up about 10 s, and up to
40-100 s while a diagram is being built.

## Sections and chapters

Each video works the same way: an opening that states the problem with numbers and examples (0:48,
1:13 and 3:42 before part one starts; graphics appear within the first 7 s), then **three numbered parts** ("Principle number one...", "Step
one..."), then a short close. Each part opens with a **full-screen chapter card**: a cream
background, a red number in a white rounded square, and the part's name in a large black serif,
held 3-5 s. Every diagram in that part is headed by the same number in a red marker circle.

## Graphics and layouts (what the editor will make)

| Type | How it looks | How often |
|---|---|---|
| **Panel + speaker** | Light-grey rounded panel (#DDE1E0) on the left 3/4 of the frame. Speaker cropped into a rounded portrait card on the right with a soft pale-blue glow. | 39-63% of runtime. The main look. |
| Marker diagram (inside the panel) | Blue, red, green and black marker on white board. Arrows, curves, boxes, labels, pyramids. Draws on in step with speech; labels underlined. | Most panels |
| Title + bullets (in the panel) | Black serif title, blue "- " bullet lines underneath, white background | A few per video |
| Screenshot (in the panel) | Real website or app screenshot, sometimes with a highlighted line | A few per video |
| Quote card | Full-screen cream (#F5F3E4). Big blue open-quote top-left, a faint giant close-quote behind on the right. Blue sans text (#2655A3), 2-4 lines, key phrase **bold**. | 1-3 per video, about 4-8 s |
| Chapter card | As above | 3 per video |
| Red buttons | Red (#C71338) rounded boxes with white serif labels over the lower half of the speaker shot, added one by one as each is named | Rare |
| Label pill | Small white pill, bottom-left, black sans ("Example 2") | Rare |
| Lower text | White bold sans text bottom-left over the speaker ("Book $10-$20") | Rare |

Graphics enter with a quick fade or a cut (they land in about 0.04-0.3 s, mostly an expo ease-out).
Motion is calm: no bounce, no spinning, no flashy transitions.

## Captions

**None.** None of the three videos has burned-in captions at any point. So the editor adds none.

## Sound

- Sound effects: very rare, 0.1-0.4 a minute (about 1-8 a video): a pop, a click, a low impact or
  a riser on a big moment. The editor will match that rate.
- Music: a quiet bed (about -22 dB) under most of every video, starting after the opening (0:46,
  1:15, 4:26) and ending before the close. **Copied** (Ayush, 2026-10-10).

## What the references do that we will not copy

These are where your decisions or single-camera footage stop us copying the references exactly.

1. **Second camera.** The references cut between a wide and a medium camera. Ayush decided
   (2026-10-10) not to imitate this: the edit stays on the one camera angle. Some punch-in zooms
   are kept, at the references' rate of framing changes (2.8 a minute, busier in the first minute).
2. **Real overhead whiteboard.** About 60% of az1Zh-FNSno is a real camera over a whiteboard with
   his hand drawing. We can't copy that; the editor will use drawn-on marker diagrams, like the
   other two videos.
3. **Photos and footage of people.** The "Example 1/2" clips and the cut-out photos of people are
   stock or real people, which the brief bans. Those moments will use a diagram, a screenshot or a
   text panel instead.
