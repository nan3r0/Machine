# p3-sets handoff

## Goal
Set layers as libass events: parallax drift, push-in, scene fade (`pipeline/visuals/sets.py`).

## Status
done. Not heavy; all tests in tests/visuals/test_sets.py ran and passed.

## What changed
- `pipeline/visuals/sets.py`: `drift_px` (capped at SET_LAYER_MARGIN_PX, sign by camera) and `set_events` (one `shape_event` per shape with `\move`, push_in adds `\org` and `\t` scale; optional dim and fade black frame shapes). Reuses `ass_kit.shape_event`.

## Decisions made
- Shapes sit at pos (0,0) via `\move(0,0,dx,0)`; the art coordinates already include the margin.
- The dim and fade shapes are built as a `Shape` with a local black palette, so they go through the same `shape_event`.
- ASS layer is ASS_LAYER_SET plus the layer's index in `art.layers`.

## Tried and abandoned
none

## Known risks
- Outline colour is looked up as `palette[outline_colour]`, as in the test fixture. Real set YAMLs must follow that.

## Next step
Compose task that uses `set_events` in scenes.ass.

## Docs
none

## Evidence
- `pytest -q` with LOOM_TASK=p3-sets: 1679 passed, 235 skipped (heavy, CI only); test_sets.py 10 passed.
- ruff clean, mypy --strict clean, tests/scope_check.py passed.
