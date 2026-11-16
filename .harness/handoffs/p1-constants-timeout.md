# Handoff: p1-constants-timeout

## Goal
Move the numbers private to `compose.py` and `qa.py` into `pipeline/constants.py` usage, and give the compose FFmpeg calls a timeout.

## Status
done. Heavy tests did not run locally; they run in CI only.

## What changed (and why)
- `pipeline/render/compose.py`: removed `_AUDIO_RATE_HZ`, `_TRUE_PEAK_DB` and `_STDERR_TAIL_LINES`. Code reads `constants.AUDIO_SAMPLE_RATE_HZ` (as `str()`), `constants.TRUE_PEAK_DBTP` (formatted `:g`, so -1.0 stays `TP=-1`) and `constants.COMPOSE_STDERR_TAIL_LINES` at call time.
- `compose._run_ffmpeg` passes `timeout=constants.COMPOSE_TIMEOUT_S`. `subprocess.TimeoutExpired` becomes `ComposeError(...) from exc`, so a hung FFmpeg fails the render instead of blocking it until the workflow limit.
- New helper `_log_partial` appends whatever FFmpeg printed before the timeout to the log. `TimeoutExpired.stderr` can be `None` or bytes even with `text=True`, so it decodes bytes and skips `None`.
- `pipeline/render/qa.py`: removed `_FPS_TOLERANCE`, `_TOOL_TIMEOUT_S` and `_STDERR_TAIL_LINES`; uses `constants.QA_FPS_TOLERANCE`, `constants.QA_TOOL_TIMEOUT_S` and `constants.QA_STDERR_TAIL_LINES`. No behaviour change.

## Decisions made
- Timeout error message names the limit (`ffmpeg timed out after 600 s`) and carries no stderr tail, since partial output may be missing; the partial output goes to the log file instead.
- The Retention removal already in `qa.py` was left as is.

## Tried and abandoned
none

## Known risks
- `COMPOSE_TIMEOUT_S` (600 s) was derived by the Architect from the whole render step, not from compose alone. Heavy tests (golden render, QA acceptance) are awaiting CI.

## Next step
Gate 2 review, then merge; then p1-phase-review.

## Docs
- architecture.md section 7: drop the compose timeout weak point (fixed here).
- workflow.md: set the p1-constants-timeout row to done.
- `.harness/status.yaml`: add p1-constants-timeout to the done tasks.
- CLAUDE.md Status: remove "a timeout on the compose FFmpeg call" and the speech-rate constants fix from the open list.
- No other doc is made false by this diff.

## Evidence
- `LOOM_TASK=p1-constants-timeout pytest tests/render -q`: 129 passed, 7 skipped (the 7 are heavy tests, not run locally).
- `pytest -q` full suite: 323 passed, 14 skipped.
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues.
