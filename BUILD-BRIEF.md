# Axis Story AI Long-Form Editor: Build Brief

Read this first. It records what Ayush (Axis Story) has decided. Build to it, and ask him before changing any decision below.

## What we're building

A fork of NextWork's open-source editor (github.com/nextwork-projects/ai-video-editor, MIT licence; keep its LICENSE and NOTICE) changed to edit **long-form YouTube videos for agency clients**. The finished videos must not look AI-edited.

## Decisions (fixed)

| Area | Decision |
|---|---|
| Input | One camera, talking head, raw footage of 30–40 min (mp4/mov). **Stay on that one angle; don't imitate the references' second camera.** Some punch-in zooms are fine, at the references' rate of framing changes (decided 2026-10-10). |
| Output | 16:9 YouTube, finished length roughly 10–20 min. One finished `render.mp4`. |
| Premiere / NLE export | **Not now.** Changes happen by asking Claude in chat. Leave `export_nle.py` alone; it isn't part of the main workflow. |
| Visuals | **Only motion graphics and animations the editor makes itself**, plus screenshots or B-roll the client supplies. **No stock B-roll (Pexels etc.) and no footage or images of real people.** |
| Music | **Use music the way the references do** (changed 2026-10-10; was "left out for now"). |
| Styles | **One style to start**, measured from the three reference videos below. Keep the per-style folder system so more styles can be added later. |
| Rendering | On Ayush's Mac (Apple Silicon). Cloud rendering later if needed. |
| Mode | **Automatic.** One approval point only: the cut, shown as a transcript with removals struck through (text, no rendering). **No visuals approval: no stills sheet, no preview clips.** Make the visuals and render. Drop every visual review step: the stills sheet, the LOOK pass where Claude inspects rendered frames, and `check.py render`. The only checks kept are the instant script checks on the plan (`check.py` plan check, `ai_tells.py --plan`). They render nothing and use no Claude usage; they just stop graphics covering the face or running off-screen. If Ayush asks for those to go too, remove them. |
| Screenshots | **Real screenshots of websites, apps and tools are allowed, and so are company logos.** Still no real people and no stock footage. |
| Captions | **Copy the reference videos' caption style exactly**: font, size, colour, position, how many words at a time, highlighting, animation, and when captions appear at all. Add nothing the references don't do. |

## Reference style (the one style)

- https://www.youtube.com/watch?v=NEi32Vn302w
- https://www.youtube.com/watch?v=m_D2yOUapNQ
- https://www.youtube.com/watch?v=az1Zh-FNSno

Measure these across their **full length**, not just the opening: cut pace over time, zoom type and frequency, caption style (or no captions), how often graphics appear and what kind, animation timing and easing, colour palette, typography, sound effects, and how sections and chapters change. Save the result as a style profile (`teardown.md` + `style.json`). Show Ayush the summary and get his sign-off before using it.

## What has to change from NextWork's version

1. **Long-form input.** Make transcription, cutting and planning reliable on 30–40 min raw footage. Process it in chunks if needed, and measure the time each stage takes on the Mac.
2. **Long-form teardown.** The creator breakdown expects TikTok/Shorts links; make it work on long YouTube videos.
3. **Long-form pacing.** Plan the edit by sections, with attention resets spaced the way the references space them. Don't stretch Shorts pacing across 20 minutes.
4. **Wide-frame layouts.** Most of the layout rules are tuned for 9:16. Tune the 16:9 placement of graphics and captions to match the references.
5. **Visuals rules.** Turn off any stock-footage or real-person sourcing. Keep client-supplied assets first, then generated motion graphics. Keep the existing "AI tells" checker on.
6. **Small changes without a full re-render.** When Ayush asks for one change ("change the graphic at 4:12", "remove the zoom at 7:30"), re-render only the affected section and splice it back into the finished video.
7. **Remove the stills approval step** from the workflow (see Mode above).
8. **Copy the references, don't invent.** Every style choice (captions, graphics, zooms, sound effects) must come from what the reference videos measurably do. If the references don't do something, the editor doesn't either.

## Order of work

1. Fork the repo into Ayush's work GitHub, install it, and run the doctor until it reports Ready.
2. Measure the three references and build the style profile. Ayush approves it.
3. Changes 1–4 (long-form handling, teardown, pacing, layouts). Test on NextWork's sample take first, then on a long test file.
4. Changes 5–8 (visuals rules, section re-render, no stills approval, copy the references only).
5. Quality pass: render a test edit and compare it with the references side by side. List every difference and fix it. Only then use it on real client footage.

## How to work with Ayush

- He wants pushback whenever you genuinely disagree. Don't just agree.
- Keep him out of technical detail. Ask only for things only he can do (approving installs, GitHub sign-in) or decide (anything that changes a decision above).
- Commit and push to his fork as you finish each stage, so nothing is lost.
