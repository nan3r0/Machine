# Handoff: p1-render-cli

## Goal
Implement `render` and `main` in `pipeline/render_one.py`: one script JSON to `final.mp4` through voice, align, captions, compose and QA.

## Status
partial, awaiting CI. The 11 non-heavy tests in `tests/test_render_one.py` pass. `test_acceptance` (heavy) is deselected locally because torch, stable-ts and ffmpeg are not installed here. A skipped heavy test is not a pass.

## What changed (and why)
- `pipeline/render_one.py`:
  - `render` validates the script with `Script.model_validate_json`, creates `out_dir`, then calls `kokoro.synthesize`, `align.align_words`, `captions_ass.build_ass` (written to `captions.ass`), `compose.compose` and `qa.run_qa`. `qa.json` is written whether QA passes or fails. All steps are called through their modules so tests can patch them.
  - `main` parses `script`, `out_dir` and `--cache-dir`, prints each failed QA check to stdout, and returns 0 (QA passed), 1 (QA failed) or 2 (invalid script, missing file, or a step error printed to stderr).
  - Compose gets `fontsdir=Path(FONTS_DIR)` (`assets/fonts`), as the earlier reviews asked. Compose's log goes to `out_dir/logs/compose.log`.

## Decisions made
- The exit-2 handler catches `ValidationError`, `OSError`, `VoiceError`, `AlignError` and `ComposeError` only, not bare `Exception`. Any other exception is a bug and shows its traceback. The docstring promise "never lets an exception escape" is then true for known failures but not for bugs; flagging this for the reviewer.
- `FONTS_DIR` is relative, so the CLI must run from the repo root (the Actions workflow and the heavy test both do).
- No owner decision was changed.

## Tried and abandoned
none

## Known risks
- The golden-render checks in `test_acceptance` (frame times, safe-zone positions, drift) have not run. They depend on the earlier heavy-test tasks being right in CI.
- `render` does not remove stale files from a reused `out_dir`; compose uses `-y` so `final.mp4` is replaced, and `qa.json` is rewritten each run.
- Local pytest needs a `tests` module shim because a `tests` package in site-packages shadows the repo's (see earlier handoffs).

## Next step
Push, let CI run the heavy test. If green, Gate 2 review, then `p1-actions-workflow`.

## Docs
- `CLAUDE.md` Status: move p1-render-cli to Done once CI is green and the task is merged.
- `workflow.md`: p1-render-cli to done only after the CI heavy test passes.
- `architecture.md` / `spec.md`: the CLI is `python -m pipeline.render_one <script.json> <out_dir> [--cache-dir DIR]`, with exit codes 0 (QA passed), 1 (QA failed), 2 (invalid script or step error), default cache dir `.cache/models`, and it passes `FONTS_DIR` as compose's `fontsdir`. Applied at close-out.
- `lessons.md`: none.

## Evidence
- `tests/test_render_one.py` via the `tests` shim, `-m "not heavy"`: 11 passed, 1 deselected.
- `ruff check pipeline/render_one.py`: clean. `mypy --strict pipeline/`: no issues in 11 files.
