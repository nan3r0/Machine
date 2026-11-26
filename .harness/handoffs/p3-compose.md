# Handoff: p3-compose

## Goal
Add a keyword-only `scenes` .ass layer to compose, burned under the captions (method A), and move captions to `CAPTION_POS_Y`.

## Status
partial, awaiting CI. Local tests pass; the heavy test `test_scenes_layer_shows_in_the_video` is skipped locally (needs ffmpeg).

## What changed (and why)
- `pipeline/render/compose.py`: `build_ffmpeg_args(..., *, scenes=None)` and `compose(..., *, scenes=None)`. With scenes the filter is `subtitles=<scenes>,subtitles=<captions>`, same fontsdir, same escaping helper. A missing scenes file raises `ComposeError` with the other inputs. Without scenes the arguments are unchanged.
- `pipeline/render/captions_ass.py`: `POS_Y = CAPTION_POS_Y` (was `HEIGHT / 2`). `HEIGHT` is still used for PlayResY.

## Decisions made
- One layer list joined with commas, instead of a second code path.

## Tried and abandoned
none

## Known risks
- The heavy render test has not run; the real libass result is unverified until CI.

## Next step
Push, open a PR (a draft is enough), and check the heavy test in CI.

## Docs
none (docstrings of both functions updated in the code).

## Evidence
- `LOOM_TASK=p3-compose .venv/Scripts/python.exe -m pytest -q --tb=short`: 1677 passed, 243 skipped (the plain command worked in the fresh venv, no namespace workaround needed).
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues in 33 files.
- `tests/scope_check.py task/p3-compose origin/main`: run after the commit, see the final report.
