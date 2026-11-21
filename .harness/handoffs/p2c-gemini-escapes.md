# Handoff: p2c-gemini-escapes (Implementer)

## Goal
Make a failed error-body read and deeply nested JSON raise GeminiError, so the weekly batch leaves one script out instead of crashing.

## Status
done. Branch `task/p2c-gemini-escapes`, committed, not pushed.

## What changed (and why)
`pipeline/script/gemini.py` only:
- `_http_message` builds the status (and 404 model) message first, then reads the body in a try. An OSError or http.client.HTTPException from the read returns the message with no excerpt. The sibling excepts in `_send_with_one_retry` do not apply inside the HTTPError handler, which is why it escaped.
- Both `json.loads` calls in `_parse_answer` catch `(ValueError, RecursionError)`. GeminiError, no retry.
- `generate_json` docstring lists both cases.

## Decisions made
- Retry rule unchanged: `_http_message` only runs on the final raise, so a 429 or 5xx with a broken body still gets its one retry.
- The key redaction still runs before the cut. When the read fails there is no body, so nothing to redact.

## Tried and abandoned
none

## Known risks
- RecursionError depth depends on the interpreter limit. Tests use 100000 nested brackets, which fails on 3.11 and 3.12.

## Next step
Gate 2 review and security review (gemini.py is a trigger). Then close-out in status.yaml.

## Docs
- Docstring of `generate_json` updated in the same change.
- workflow.md Phase 2c status row and `.harness/status.yaml`: applied at close-out.
- architecture.md, PRD.md, lessons.md: none.

## Evidence
Run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe` (system `tests` package shadows the repo's).
- `tests/script/test_gemini_errors.py`, `test_gemini.py`, `test_gemini_shapes.py`, `test_gemini_redirect.py` with `LOOM_TASK=p2c-gemini-escapes`: 69 passed.
- Full `pytest -q`: 1235 passed, 30 skipped.
- `ruff check .`: passed. `mypy --strict pipeline/`: 22 files, no issues.
