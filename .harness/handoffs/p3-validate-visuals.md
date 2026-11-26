# p3-validate-visuals

## Goal
`validate.problems` checks scene `visual.data` (set, pose, camera, items) and its caps.

## Status
partial: code done, blocked on a locked-test bug (see CONTRACT_CHANGE.md). 43 of 44 tests in tests/script/test_validate_visuals.py fail at `Script.model_validate` (strict schema rejects the string `publish_after`), before reaching validate.

## What changed (and why)
- `pipeline/script/validate.py`: new `_visual_problems` (called from `problems`), `_item_problems`, `_item_text_problems`. Rules: only set/pose/camera/items keys; set/pose/camera in `SET_IDS`/`POSES`/`CAMERA_MOVES` (so `HOST_BACKDROP_SET` is rejected); items only on chart/steps/map, 1 to `VISUAL_ITEMS_MAX` string-only `{label, value}`; chart with 2+ items needs plain-number values; steps values all empty or all set; map exactly one item; label non-blank, label/value caps, each through `_text_problem`; at most `VISUAL_DATA_SCENES_MAX` scenes with items; label+value total at most `VISUAL_TEXT_MAX_CHARS`. Messages: "scene N field: ...". Docstring rules updated.

## Decisions made
- Plain number = ASCII digits with thousands commas and an optional decimal part. A chart with one item may have any text value (test requires "eight years").
- `items` present counts as a data scene, whatever its validity.

## Tried and abandoned
none

## Known risks
- Locked test needs the fix in CONTRACT_CHANGE.md. Verified logic with a temp copy using `strict=False`: 43 of 44 pass; the last is the `Script.model_validate(SAMPLE)` line in test_acceptance, same cause.

## Next step
Owner/orchestrator fixes the locked test, then re-run this task's tests.

## Docs
none (the validate.py docstring is updated; PLAN/spec need nothing).

## Evidence
ruff clean, mypy --strict clean. Full pytest: 1657 passed, 214 skipped, 43 failed, all 43 in test_validate_visuals.py (strict date error). Temp copy with `strict=False`: 43 passed, 1 failed (same cause).
