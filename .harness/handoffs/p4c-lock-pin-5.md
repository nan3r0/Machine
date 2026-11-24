# p4c-lock-pin-5

## Goal
Put num2words back to 0.5.6 (0.5.14 pulls in docopt, which has no pinned sdist-free lock entry) and stop Dependabot bumping num2words, docopt and srsly.

## Status
partial: awaiting install proof (render.yml dispatch on main after merge; CI Gate 1 does not install the locks).

## What changed (and why)
- requirements-render.txt: the num2words==0.5.14 block (pin plus two hashes) replaced by the 0.5.6 block (pin plus one hash), copied by script from `git show f73b9d2^:requirements-render.txt` lines 114-115 with the block shape asserted. Nothing else changed.
- .github/dependabot.yml: bare ignores for num2words, docopt and srsly in the pip entry. Existing ignores and the pydantic group kept.

## Decisions made
Bare ignores (no update-types) so a bump cannot move a cap unnoticed. PR #169 (srsly 3.0.1) is not merged; the orchestrator closes it.

## Tried and abandoned
none

## Known risks
render.yml may fail on another package; if so report which, do not guess.

## Next step
Merge, then the owner dispatches render.yml on main.

## Docs
none

## Evidence
`LOOM_TASK=p4c-lock-pin-5 pytest tests/test_lock_consistency.py` (temporary tests/__init__.py, removed): 12 passed. ruff check . clean. docs_check passed.
