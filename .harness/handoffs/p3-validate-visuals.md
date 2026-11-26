# p3-validate-visuals

## Goal
`validate.problems` checks scene `visual.data` (set, pose, camera, items) and its caps.

## Status
done. The locked test bug (strict `Script.model_validate` with a date string) was ruled on by the Architect (plan branch `plan/p3-validate-visuals-tests`, merged into this branch). CONTRACT_CHANGE.md dropped.

## What changed (and why)
- `pipeline/script/validate.py`: new `_visual_problems` (called from `problems`), `_item_problems`, `_item_text_problems`. Rules: only set/pose/camera/items keys; set/pose/camera in `SET_IDS`/`POSES`/`CAMERA_MOVES` (so `HOST_BACKDROP_SET` is rejected); items only on chart/steps/map, 1 to `VISUAL_ITEMS_MAX` string-only `{label, value}`; chart with 2+ items needs plain-number values; steps values all empty or all set; map exactly one item; label non-blank, label/value caps, each through `_text_problem`; at most `VISUAL_DATA_SCENES_MAX` scenes with items; label+value total at most `VISUAL_TEXT_MAX_CHARS`. Messages: "scene N field: ...". Docstring rules updated.

## Decisions made
- Plain number = ASCII digits with thousands commas and an optional decimal part. A chart with one item may have any text value (test requires "eight years").
- `items` present counts as a data scene, whatever its validity.

## Tried and abandoned
none

## Known risks
- The scope check fails until the plan branch merges to main (the locked test differs from origin/main). Passes after the merge.

## Next step
Owner/orchestrator fixes the locked test, then re-run this task's tests.

## Docs
none (the validate.py docstring is updated; PLAN/spec need nothing).

## Evidence
ruff clean, mypy --strict clean. Full pytest after merging the plan branch: 1700 passed, 214 skipped. Gate 2 and security review: approve, no blocking findings.
