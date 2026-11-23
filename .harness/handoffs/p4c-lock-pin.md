# p4c-lock-pin

## Goal
Put pydantic-core back in step with pydantic in requirements-generate.txt and stop Dependabot bumping it alone.

## Status
partial: awaiting install proof (Linux `pip install --require-hashes -r requirements-generate.txt`; CI Gate 1 does not run it).

## What changed (and why)
- requirements-generate.txt: pydantic-core 2.50.5 to 2.50.4 (what pydantic 2.14.3 requires). The old hash block (141 lines, for 2.50.5) is replaced by the one `--hash` line 2.50.4 has in requirements-render.txt, copied, not newly computed. Nothing else in the file changed.
- .github/dependabot.yml: `ignore: - dependency-name: pydantic-core` on the pip entry. A pydantic-core bump now comes only with a pydantic bump and a lock regenerate.

## Decisions made
- Used Write for requirements-generate.txt because the 141-line hash block is too large for one Edit match; other lines were reproduced unchanged.

## Tried and abandoned
none

## Known risks
- The render lock has one hash for 2.50.4 (one wheel). The generate lock is for ubuntu-latest x86_64 CPython 3.12, as is the render lock's, so it should match, but only an install proves it.
- The test does not prove the set resolves (see p4c-lock-pin-contracts handoff).

## Next step
Owner dispatches weekly-scripts on the task branch (or waits for the next run after merge); if "Install light requirements" passes, mark done. Orchestrator owes the lessons.md entry.

## Docs
none in this task's paths. Owed at close-out: lessons.md entry (a bump of one package in a hashed lock must keep the lock consistent; locks must agree; pydantic-core is ignored by Dependabot).

## Evidence
- `LOOM_TASK=p4c-lock-pin pytest tests/test_lock_consistency.py` (with the `tests.__path__` shim): 6 passed.
- Full suite without LOOM_TASK (shim): 1601 passed, 98 skipped. `pytest .harness/tests`: 90 passed.
- `ruff check .` clean. `python tests/docs_check.py` passed.
