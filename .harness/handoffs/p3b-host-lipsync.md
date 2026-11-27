# Handoff: p3b-host-lipsync

## Goal
Host mouth follows the voice loudness: closed in silence and between syllables, no long open holds, without re-cutting the body.

## Status
done (local gates green). Heavy tests are not involved.

## What changed (and why)
- `pipeline/visuals/character.py` only.
  - `_mouth_states` runs the state machine over MOUTH_WINDOW_S windows (open/close levels, hold, open cap, gate to the narration span, shape from MOUTH_SHAPES).
  - `_window_level` gives the level; `levels=None` uses 1 inside a word span.
  - `host_events` emits body, eyes, brows and arms cut only at bob half-cycles and blinks (`_boundaries` no longer takes word edges). The mouth is emitted as its own runs, cut at mouth changes and bob half-cycles, each with its own bob `\move`.
  - Closed mouth is the pose mouth if in HOST_CLOSED_MOUTHS, else "rest". `_mouth_at` removed.
- Docstring unchanged.

## Decisions made
- A forced close (outside the narration) ignores the hold, so a breath after the last word never opens the mouth.
- Window index is absolute (`t / MOUTH_WINDOW_S`), so `levels` is on the voice timeline, same as the timings.
- Shape changes while open count as state changes and obey MOUTH_HOLD_S; the open cap counts from when the mouth last opened.

## Tried and abandoned
none

## Known risks
- MOUTH_* values are not retuned (the locked tests pass with the constants as they are). The owner should check the first render from p3b-lipsync-wiring.
- Mouth events are now separate from the face events, so a mouth cut adds only mouth events.

## Next step
p3b-lipsync-wiring (waits for PR #206).

## Docs
none (the architecture.md weak-point note and the CLAUDE.md status are already listed in the p3b-plan handoff).

## Evidence
- Tests run through a sys.path shim because of the site-packages `tests` package (lessons 2026-11-15): test_host_lipsync.py + test_character.py 27 passed; tests/visuals + test_render_one_visuals.py 82 passed, 30 skipped.
- ruff check clean; mypy --strict pipeline/ clean (34 files).
