# Handoff: p4d-gemini-quota-guard (implementer)

## Goal
Stop the weekly batch from spending Gemini requests that cannot succeed (daily-quota 429, outage) and log the real request count.

## Status
done. Gate 1 green locally; no heavy tests involved. Gate 2 plus security review next (gemini.py and batch.py match the security trigger).

## What changed (and why)
- `pipeline/script/gemini.py`: `GeminiQuotaError(GeminiError)`; module-level `requests_sent`, incremented once per request handed to the opener (before `open`, so never on a missing key); the error body is read once by `_read_body` (key redacted before any cut, `None` when reading fails) and shared by detection (`_PER_DAY`, a case-insensitive "per day" or "perday" regex on the full body, 429 only) and `_http_message` (excerpt of 200 characters). A daily-quota 429 raises at once with no sleep, also on the retry. Docstring of `generate_json` updated.
- `pipeline/script/batch.py`: `run` notes `gemini.requests_sent` at the start and logs "<N> Gemini requests" in the summary line (all paths after the "no unused source" exit). GeminiQuotaError stops the loop; GeminiErrors in a row (`GEMINI_MAX_CONSECUTIVE_ERRORS`) stop it; a written script or GenerateError resets the streak. `_check_and_repair` re-raises GeminiQuotaError from a rewrite (script left out). `pr_body` has keyword-only `stopped: str | None = None` and writes "Stopped early: <fixed text>" after the heading and the exhausted line. Docstrings of `run` and `pr_body` updated.

## Decisions made
- Stop reason is one of two fixed strings built in `run`; the same text goes to the warning and the PR line. No error text reaches the PR line.
- The error body is read for every HTTPError (not only 429): the cost is nil and it keeps one code path.
- Exit codes unchanged.

## Tried and abandoned
none

## Known risks
- The real Google daily-quota body is not captured; if it differs from "per day"/"PerDay", behaviour degrades to the old retry plus the streak stop.
- A per-minute 429 whose details also list a per-day quota id would count as the daily quota and stop the batch early.
- A batch still needs 14 to 28 writer calls against 20 a day on the free tier; this task does not fix that (owner decision).

## Next step
Gate 2 and security review; merge; then the Docs below at close-out.

## Docs
Outside my paths_allowed, to apply at close-out:
- architecture.md section 7 (real requests reaching twice the cap): a daily-quota 429 is not retried; the batch stops on it or after `GEMINI_MAX_CONSECUTIVE_ERRORS` errors in a row; the run logs the real request count ("<N> Gemini requests").
- docs/runbook.md, red weekly-scripts runs: "Stopped early: Gemini daily quota used up" or "Stopped early: 3 Gemini errors in a row" in the PR or the log; the unused sources are picked again next run.
- docs/threat-model.md: no new surface; the stop line is fixed text (optional note).
- `.harness/status.yaml`: mark p4d-gemini-quota-guard done after merge.
- CLAUDE.md Status: add the Gemini quota guard to the done list after merge.
Docs inside my paths_allowed: the module and function docstrings, done.

## Evidence
- `pytest -q -m "not heavy"`: 1502 passed, 232 skipped (skips are CI-only shell/heavy tests). New files test_gemini_quota.py and test_batch_stop.py pass.
- `ruff check .` clean; `mypy --strict pipeline/` clean; `python tests/docs_check.py` passed; `tests/scope_check.py task/p4d-gemini-quota-guard p4d-quota-guard-contracts` passed.
