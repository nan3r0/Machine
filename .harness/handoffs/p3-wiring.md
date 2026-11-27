# p3-wiring handoff

## Goal
render_one writes `out_dir/scenes.ass` from `router.build_scenes_ass(script, timings)` after alignment and passes it to compose as `scenes=` (milestone M1, Method A).

## Status
partial: awaiting CI. The non-heavy test passes locally; `test_acceptance` (heavy, both demo scripts, render budget, frames) skips locally and runs in CI only.

## What changed (and why)
- `pipeline/render_one.py` only: import `pipeline.visuals.router`, call `router.build_scenes_ass(script, timings)` between align and compose, write `scenes.ass` (utf-8), pass `scenes=scenes_path` to `compose.compose`. Steps are still called through their modules so tests can fake them. Exit codes unchanged. Docstrings updated.

## Decisions made
- No new error handling: a router failure propagates and exits 2 through the existing boundary in `main`.
- ASS injection check: every Gemini-sourced text in cards and charts reaches events only through `ass_kit.text_event`, which calls `captions_ass.escape_ass_text` (escapes `{`, `}` and backslash). The other `dialogue(...)` callers (`ass_kit` shapes, `cards._drawing`) emit only drawing paths and constants. Nothing reaches an event unescaped. Not tested with a hostile script here (outside this task's paths); the escape function has its own tests.

## Tried and abandoned
none

## Known risks
- Heavy acceptance not run locally (no ffmpeg/torch by rule). Render time with scenes under `RENDER_BUDGET_S` is unproven until CI.
- Negative-x and push-in checks are on the M1 render (p3-sets-art backlog).

## Next step
Open a draft PR so CI runs the heavy tests. Then owner dispatches M1 (below).

Owner dispatch for M1: from the Actions page run `render.yml` on branch `task/p3-wiring` twice, once with `queue/approved/sample-65s.json` and once with `tests/fixtures/scripts/demo-data.json`. Visual QA reviews both frames artifacts (golden frames and the 8-frame strip, plus the consecutive step frames). The owner watches both mp4s before merge.

## Docs
- CLAUDE.md Status and `.harness/status.yaml` at close-out (p3-wiring done after M1 approval). No doc is made false by this diff; none inside paths_allowed.

## Evidence
- `LOOM_TASK=p3-wiring`, full suite with the seeded `tests` namespace command from p3-sets-art Evidence: 1804 passed, 118 skipped (heavy and not-yet-done tasks) before the final line-wrap edits; `tests/test_render_one.py` re-run after: 13 passed, 1 skipped.
- `test_writes_scenes_ass_and_passes_it_to_compose` passes. `test_acceptance` skipped (heavy).
- `mypy --strict pipeline/`: no issues in 33 files. `ruff check .`: see final run below in report.
- `tests/scope_check.py task/p3-wiring origin/main`: passed (run before commit, 0 changed files seen; rerun after commit).
