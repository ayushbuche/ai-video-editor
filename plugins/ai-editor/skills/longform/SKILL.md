---
name: longform
description: Edits a long-form 16:9 YouTube video for an Axis Story client, start to finish, in a measured house style (styles/<name>/). Takes one raw single-camera talking-head take (mp4/mov, 5-40 min), cuts the retakes and pauses, has the user approve the cut by watching it (the only approval), then plans and renders the graphics, music and sound without further sign-off. Use when the user says "edit this client video", "edit my client's video", "long-form edit", drops a long take, or asks to change one part of a finished edit ("change the graphic at 4:12", "remove the zoom at 7:30"). Not for Shorts or vertical clips (clips), not for measuring a new reference style (creator-teardown), and not for a product video (product-video).
license: MIT
compatibility: Everything the setup skill installs (Python venv, ffmpeg, Node, Remotion). Renders on the Mac. Runs from the full ai-editor plugin folder.
---

# Long-form edit

Paths: `${CLAUDE_SKILL_DIR}` means the folder containing this SKILL.md, and `${CLAUDE_PLUGIN_ROOT}` the plugin folder two levels above it.

Every question to the user goes in the question box: call the AskUserQuestion tool (2-4 options, the recommended one first). Only in an agent without that tool, ask numbered questions in text.

`C="${CLAUDE_PLUGIN_ROOT}/skills/cut/scripts"`, `S="${CLAUDE_PLUGIN_ROOT}/skills/style-edit/scripts"`,
`PY="python3 ${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/run.py"` (the editor's venv). On Windows, use `py` wherever
these commands say `python3`.

Read `BUILD-BRIEF.md` at the repo root first: Ayush's decisions. They beat anything here, and anything in
PRINCIPLES.md or another skill that disagrees. Ask him before changing one.

**One approval: the cut.** No stills sheet, no preview clips, no looking at rendered frames to judge them.
After the cut is approved, plan, check and render without asking.

## 1. Cut

`<name>` is a slug of the file name. Never touch the source file.

```bash
$PY "$C/transcribe.py" <source> edits/<name>/words.raw.json      # about 1 min per 10 min of footage
python3 "$C/retakes.py" propose edits/<name>
```

Write `spans.json` (cut skill, `references/retake-detection.md`): last take wins, quote the transcript.
Then build, read `paper-edit.md` straight through, render and verify, exactly as the cut skill's steps 3-5:

```bash
python3 "$C/build_timeline.py" <source> edits/<name> --max-pause 0.3
python3 "$C/render.py" <source> edits/<name>
$PY "$C/verify_cut.py" edits/<name>
$PY "$C/join_audit.py" edits/<name>
python3 "$C/preview_cut.py" edits/<name>
```

`verify_cut.py` re-hears the whole cut with the engine that made `words.raw.json` (its `.meta.json`); never
pass another `--engine`. `join_audit.py` then hears every join on its own, where a whole-file pass smooths over
a doubled word, a clipped word or a scrap of a removed one (about 5-8 min for a 25-min cut). Act on every flag
it reports as heard in 2 or more listens and on every FRAGMENT: a real repeat or survivor gets the span it
prints; a clipped word is a `build_timeline.py` fault (below). "Heard once only" is usually the window
mishearing: leave it unless the words either side of that join read wrong in `paper-edit.md`. One fix cycle
(build, render, verify, join audit), then hand over.

Pauses follow the references (0.2-0.3 s between sentences): always pass `--max-pause 0.3`, because the
taste file's `cut.max_pause` is a Shorts setting (0.1). Every pause and breath over 0.3 s is cut, the intro
included (Ayush, 2026-10-13: "relatively fast-paced"); every word rings out before a cut. The
page underlines words that play though the first transcript missed them.

**The approval is watching the cut** (Ayush, 2026-10-13: he reviews by watching, not the page). Give him the
path to `cut.mp4` (too big to send) and, in a few lines, the joins still worth a listen: the time in the cut,
the words either side, and what may be wrong. Then **wait for the cut approval.** A
note about a word clipped or a join that sounds wrong is a timing fault in `build_timeline.py`: fix it there
(with a test in `test_build_timeline.py`), not by hand in this edit.

## 2. Board: what goes on screen, and when

Write `edits/<name>/board.json` (shape: the docstring of `$S/longplan.py`). This is the creative call, and
it is yours. Read `references/graphics.md` before writing it: what earns a graphic, which kind, and the
rules each kind follows. Quote the speaker's words from `words.json` for every time; never type a number.

Anything the client supplied (screenshots, logos, thumbnails, their own episode or video) goes in
`edits/<name>/images/` and on screen first. The client's own content may show people; nothing else may
(no stock footage, no photos of real people).

## 3. Music

The bed runs from after the opening to before the sign-off, about 22 dB under the voice, as the references
do. Use the track the user named; with none, a free track that needs **no credit** and no sign-in (Mixkit's
free licence; never CC BY: Ayush, 2026-10-13), its source and licence in `edits/<name>/audio/MUSIC-LICENSE.md`.
The level is the style's (`style.json` sound.music.level_db).

## 4. Plan and check

```bash
$PY "$S/face.py" edits/<name>
$PY "$S/longplan.py" edits/<name> --music audio/<track>
```

It prints the pacing next to the references (information, not a target) and the instant checks. Fix every
FAIL in `board.json` and plan again: a graphic over silence, one too short to read, overlaps, diagram text off
the panel, words over the chin, a script line that is not in the transcript.

## 5. Render

```bash
python3 "$S/edit.py" render edits/<name>
```

About 1 minute of rendering per minute of video on the Mac. Then confirm the voice survived the render
(it must match the cut within 0.5 dB, with no dropouts) and hand over `edits/<name>/render.mp4`: send it
to the user (SendUserFile) and give its path.

## 6. Notes on the finished edit

A note about one graphic or one moment changes `board.json` (or a template, if it is a rule for every
video: then also record it in `references/graphics.md` and, if it is a decision, in the brief). Plan
again and render. A note about the cut goes back to step 1.

## Files

- `references/graphics.md`: what goes on screen, every rule Ayush has set.
- `$S/longplan.py` (board -> plan, checks), `$S/diagrams.py` (marker diagrams), `$S/edit.py` (render),
  `${CLAUDE_PLUGIN_ROOT}/remotion/src/LongEdit.tsx` (the renderer). Each script has a `demo` self-check.
- `styles/<name>/teardown.md` + `style.json`: the measured reference style.
