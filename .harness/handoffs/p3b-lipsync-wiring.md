# Handoff: p3b-lipsync-wiring

## Goal
Read voice.wav loudness and pass it through the router to the host (lip flap).

## Status
partial. Implementation done and passing, except the locked `tests/test_lipsync_wiring.py::test_acceptance`, which is broken (see CONTRACT_CHANGE.md). The owner still has to dispatch render.yml for sample-65s and watch the mouth.

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
- `test_acceptance` shares one `monkeypatch` between both halves; the first half's fake `build_scenes_ass` leaks into the second, so the router half sees `got == []`. Both halves pass alone. Needs the locked test fixed (CONTRACT_CHANGE.md).
- No render seen yet, so no tuning advice for the MOUTH_* thresholds.

## Next step
Owner: fix the acceptance test per CONTRACT_CHANGE.md, dispatch render.yml on this branch for sample-65s, watch the mouth, and report numbers if it is too lazy or too busy.

## Docs
none

## Evidence
- `ruff check .` clean; `mypy --strict pipeline/` clean.
- pytest on tests/voice/test_levels.py, tests/test_lipsync_wiring.py, tests/visuals, tests/test_render_one.py: 102 passed, 30 skipped, 1 failed (test_acceptance, test bug above).
