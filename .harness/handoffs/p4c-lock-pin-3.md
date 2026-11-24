# Handoff: p4c-lock-pin-3

## Goal
Put curated-transformers back to 0.1.1 (spacy-curated-transformers 0.3.1 needs >=0.1.0,<0.2.0) and stop Dependabot bumping the curated stack.

## Status
partial, awaiting install proof (CI Gate 1 does not install the locks).

## What changed (and why)
- `requirements-render.txt`: curated-transformers 0.9.1 to 0.1.1, block copied from `git show e2f92bb^:requirements-render.txt` by a script that asserts the block (one hash line). Nothing else changed.
- `.github/dependabot.yml`: curated-transformers ignore is now bare (all versions); added bare ignores for curated-tokenizers and spacy-curated-transformers. thinc ignore and pydantic group kept.

## Decisions made
Bare ignores because 0.x minor bumps are not caught by the semver-major rule.

## Tried and abandoned
none

## Known risks
num2words, filelock and rfc3986 bumps merged unchecked in the same batch; the render.yml dispatch is their install proof. If it fails on one, report which.

## Next step
After merge, owner dispatches render.yml on main (Linux install with `--require-hashes`).

## Docs
none

## Evidence
`LOOM_TASK=p4c-lock-pin-3 pytest tests/test_lock_consistency.py tests/test_render_lock.py -q --tb=short`: 16 passed (temporary empty tests/__init__.py, removed). `ruff check .` clean. `python tests/docs_check.py` passed.
