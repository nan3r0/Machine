# p4c-lock-pin-4

## Goal
Put rfc3986 back to 1.5.0 (csvw 4.2.0 needs rfc3986<2) and stop Dependabot bumping rfc3986 and csvw.

## Status
partial: awaiting install proof (CI Gate 1 does not install the locks; owner dispatches render.yml on main after merge).

## What changed (and why)
- requirements-render.txt: the rfc3986==2.0.0 block (pin plus two hashes) replaced by the 1.5.0 block (pin plus one hash), copied by script from `git show 3561720^:requirements-render.txt` with the block shape asserted. Nothing else changed.
- .github/dependabot.yml: bare ignores for rfc3986 and csvw in the pip entry. Other ignores and the pydantic group kept.

## Decisions made
Bare ignores (no update-types) so a csvw bump cannot move its own rfc3986 cap unnoticed.

## Tried and abandoned
none

## Known risks
render.yml may fail on another package; if so report which, do not guess.

## Next step
Merge, then owner dispatches render.yml on main.

## Docs
none

## Evidence
`pytest tests/test_lock_consistency.py tests/test_render_lock.py` (LOOM_TASK=p4c-lock-pin-4, temporary tests/__init__.py): all pass. ruff check . clean. docs_check passed.
