# Handoff: p2b-gemini-shapes

## Goal
Phase review N5: odd Gemini response shapes and failed body reads raise `GeminiError`, so one bad call leaves one script out instead of crashing the weekly batch.

## Status
done. Awaiting Gate 1 in CI and the security specialist review (gemini.py is a trigger).

## What changed (and why)
`pipeline/script/gemini.py` only:
- `_parse_answer`: a `steps` that is not a list, or a model_output step whose `content` is not a list, raises `GeminiError("Gemini response has an unexpected shape")`. Before, this was a TypeError the batch does not catch. Non-dict steps and parts, non-model_output steps, and the no-text error are unchanged. A missing `steps` or `content` key still defaults to an empty list.
- `_send_with_one_retry`: a last `except (OSError, http.client.HTTPException)` raises `GeminiError` at once, no retry, message `Gemini request failed: <ExceptionType>` (type name only, never the key). It sits after the TimeoutError and URLError branches, since both are OSErrors with their own rules, so a read timeout keeps its retry.
- `generate_json` docstring rules list names both.

## Decisions made
- Content check happens only for model_output steps, so an odd `content` on a step of another type is still skipped, as before.
- The handler also covers errors raised while opening the connection (for example ConnectionResetError at connect), not just the body read. Same rule applies, so it is consistent.

## Tried and abandoned
none

## Known risks
- A transient connection reset is no longer retried (plan decision: only 429, 5xx and timeouts retry). That costs one script per such failure, never a crash.

## Next step
Gate 1 CI, security review, Gate 2, merge.

## Docs
none. No doc describes these failure paths; PRD, spec and architecture are unaffected. Close-out may tick N5 in the phase 2b status.

## Evidence
- `.venv/Scripts/python.exe -m pytest tests/script -q`: 633 passed, 30 skipped (includes `tests/script/test_gemini_shapes.py`, all pass).
- `ruff check pipeline/script/gemini.py` and `mypy --strict pipeline/script/gemini.py` clean (ruff re-run after wrapping one docstring line).
- Global python has a stray `tests` package; the task venv's interpreter avoids the shadowing (lessons.md, 2026-11-15).
