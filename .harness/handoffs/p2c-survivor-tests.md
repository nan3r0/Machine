# Handoff: p2c-survivor-tests (Test Author)

## Goal
Write one behaviour test for each real mutation gap the Architect listed in `.harness/handoffs/p2c-plan.md` (2026-11-21 report, CI run 44942078820). No new triage.

## Status
done. Branch `task/p2c-survivor-tests`, committed, not pushed. Every new test passes on current code, so no pipeline bug turned up.

## What changed (and why)
- `tests/script/test_survivors.py` (new, 27 tests):
  - gemini, through `FakeUrlopen` with `time.sleep` patched:
    - text split over two model_output steps is joined in step order, with a thought step in between that is ignored;
    - seven bad parts are skipped (non-dict, a string, None, a thought part carrying text, a text part with no text, text 5, text None), each put before the real text part;
    - two bare timeouts: GeminiError, 2 requests, one sleep;
    - URLError(TimeoutError) is retried once and succeeds; twice is GeminiError after 2 requests;
    - URLError(ConnectionRefusedError) is GeminiError after 1 request with no sleep. A success is queued second, so a mutant that retries would return instead of raising;
    - an HTTP 400 whose body is not UTF-8 and holds the key: GeminiError without the key, 1 request.
  - batch, using the `test_batch.py` helpers (imported, not edited):
    - `out_dir` under a missing `out/` returns 0 and writes `pr_body.md`;
    - `rewrite_line` gets the checker's reason. The reason string appears nowhere else, unlike the old "1850" test, where the old narration also carried it;
    - a writer that always raises GenerateError is called `SCRIPT_ATTEMPTS` times for that script, the script is left out, and its id is in the body;
    - the PR body numbers scenes from 1, like the flags. The test reads the last "scene N" before each narration, so it does not depend on the `_code` span layout.
  - validate:
    - the whole set of code points outside Nd, Nl and No whose NFKD form holds an ASCII digit is rejected in the hook, with the problem naming the code point. The set is computed at test time from the contract, not from `_hides_ascii_digit`. It has 80 members on 3.11 and is checked to include U+32C0, U+3358 and U+32C8;
    - `x://y` and `www.` with no TLD, in several cases, are URLs. These inputs never match the bare-domain regex;
    - narration of exactly `NARRATION_MAX_CHARS` passes. One more letter in the same word gives exactly one problem, a narration one, with the word count unchanged.
  - sources: `bloop` loads before `bloop-2`.
  - `test_acceptance` runs one case from each module.

## Decisions made
- I assert on behaviour (request counts, sleeps, which field has a problem, the code point in it), never on message wording. The plan rules out pinning wording.
- I used a size lower bound (more than 50) for the hidden-digit set instead of `== 80`, because CI runs Python 3.12 and the Unicode tables differ between versions.

## Tried and abandoned
none

## Known risks
- I could not run mutmut locally (no Windows support). Each test is built so the planned mutant changes what it observes, but the kills are only confirmed by the next CI reports run.
- p2c-gemini-escapes changes `_http_message`. The non-UTF-8 test only checks GeminiError, that the key is absent and the request count, so it should still hold after that change.

## Next step
Gate 2 review, merge, close-out (status.yaml), then dispatch `ci.yml` on main for a fresh mutmut report, only after the close-out merges (lessons.md 2026-11-21).

## Docs
- Inside paths_allowed: none.
- Owed at close-out:
  - add `p2c-survivor-tests` to `.harness/status.yaml` `done`;
  - the workflow.md Phase 2c status row;
  - the CLAUDE.md Status line ("Next: the Phase 2c tasks"), once this task and p2c-gemini-escapes have both closed.
- lessons.md: none, no mistake found.

## Evidence
Run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe` (the `tests` package shadowing, lessons.md 2026-11-15).
- `LOOM_TASK=p2c-survivor-tests pytest -q tests/script/test_survivors.py`: 27 passed, 0 skipped.
- `LOOM_TASK=p2c-survivor-tests pytest -q`: 1243 passed, 49 skipped. That is main's 1216 plus the 27 new tests. The 49 skips match main: other tasks' locked tests (such as `test_gemini_errors.py`), Windows-only tests and heavy tests. None of them is in `test_survivors.py`.
- `ruff check .`: all checks passed. `python tests/docs_check.py`: passed.
- Hidden-digit set on Python 3.11: 80 code points.
