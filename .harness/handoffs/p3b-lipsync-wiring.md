# Handoff: p3b-lipsync-wiring

## Goal
Read voice.wav loudness and pass it through the router to the host (lip flap).

## Status
partial, awaiting CI and the owner's render. The acceptance test was fixed by the Architect (plan/p3b-lipsync-wiring-tests) and passes. The owner still has to dispatch render.yml for sample-65s and watch the mouth.

## What changed (and why)
- `pipeline/voice/levels.py`: `voice_levels` implemented (stdlib wave + numpy): window RMS over the 95th percentile, capped at 1, partial last window dropped, ValueError for non mono 16-bit.
- `pipeline/visuals/router.py`: `levels=levels` passed to both `host_events` calls.
- `pipeline/render_one.py`: `levels.voice_levels(voice_path)` after the voice is written, passed to `build_scenes_ass`.

## Decisions made
- Window size is `round(framerate * MOUTH_WINDOW_S)`. MOUTH_* constants untouched.
- Files shorter than one window return `[]`.

## Tried and abandoned
none

## Known risks
- No render seen yet, so no tuning advice for the MOUTH_* thresholds.
- Levels are normalised by the 95th percentile: if over 95% of windows are silent but some sound exists, every level is 0 and the mouth never opens. Not realistic for narration.
- A non-PCM wav raises `wave.Error`, not the documented ValueError. kokoro writes mono 16-bit PCM, so it cannot happen today; render_one.main exits 2 either way.

## Next step
Owner: dispatch render.yml on this branch for sample-65s, watch the mouth, and report numbers if it is too lazy or too busy.

## Docs
none

## Evidence
- `ruff check .` clean; `mypy --strict pipeline/` clean.
- pytest on tests/voice/test_levels.py, tests/test_lipsync_wiring.py, tests/visuals, tests/test_render_one.py, tests/test_render_one_visuals.py: 103 passed, 33 skipped.
