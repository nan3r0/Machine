# p2-gemini-redirects (Implementer)

## Goal
CSO P2-5: the Gemini client must never follow an HTTP redirect, so the `x-goog-api-key` header cannot be re-sent to another host.

## Status
done. Branch `task/p2-gemini-redirects`, committed, not pushed.

## What changed (and why)
- `pipeline/script/gemini.py` only:
  - New `_NoRedirect(HTTPRedirectHandler)` whose `redirect_request` returns None, and a module-level `_OPENER = urllib.request.build_opener(_NoRedirect)`.
  - `_send_with_one_retry` sends with `_OPENER.open(request, timeout=constants.GEMINI_TIMEOUT_S)` instead of `urlopen`. A 3xx now raises HTTPError, which the existing non-retryable path turns into `GeminiError("Gemini HTTP <code>: ...")`.
  - The `generate_json` docstring names the opener and lists any 3xx among the immediate, no-retry failures.
- Nothing else touched. The endpoint is still read from `constants.GEMINI_ENDPOINT` at call time.

## Decisions made
- The opener is built once at import, not per call. It holds no state, so one shared instance is simpler.
- The `redirect_request` override takes `*args, **kwargs` to match urllib's signature without repeating its six parameters.

## Tried and abandoned
none

## Known risks
- The module docstring still says only "standard library only"; it never mentioned `urlopen`, so no change was needed there.
- Proxy env vars: `build_opener` keeps the default `ProxyHandler`, so proxy behaviour is the same as with `urlopen`.

## Next step
Gate 2 review plus the security specialist review (gemini.py is a trigger in `.harness/config.yaml`), then merge.

## Docs
- None needed beyond the docstring edit in `gemini.py`.
- At close-out: the threat-model row for P2-5 can be marked mitigated (CSO at phase end). architecture.md and spec.md do not mention how the client sends, so no change there.

## Evidence
- `LOOM_TASK=p2-gemini-redirects pytest -q tests/script/test_gemini_redirect.py tests/script/test_gemini.py`: 39 passed (301, 302, 303, 307, 308 refused with no hit on the target; direct control passes; acceptance passes).
- `ruff check .`: all checks passed.
- `mypy --strict pipeline/`: no issues in 21 files.
- `pytest -q --tb=short` (no LOOM_TASK): 731 passed, 425 skipped.
- Venv used: `../p2-weekly-workflow/.venv`.
