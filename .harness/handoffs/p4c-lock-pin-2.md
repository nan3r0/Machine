# Handoff: p4c-lock-pin-2

## Goal
Make requirements-generate.txt and requirements-render.txt resolvable again after the Dependabot bumps, and group pydantic with pydantic-core.

## Status
partial, awaiting install proof (CI Gate 1 installs neither lock).

## What changed (and why)
- requirements-generate.txt, requirements-render.txt: pydantic-core 2.50.4 to 2.50.5 (140 hash lines copied from ba7bbd0), because pydantic 2.14.4 requires exactly 2.50.5.
- requirements-render.txt: thinc back to 8.3.14 (block from 9aca65d^) and curated-transformers back to 0.1.1 (block from e2f92bb^), because spacy and spacy-curated-transformers cap them.
- .github/dependabot.yml: removed the pydantic-core ignore; ignore semver-major for thinc and curated-transformers; group pydantic and pydantic-core.
- Blocks were copied by a script reading `git show`, not typed. No hash invented.

## Decisions made
None beyond the task notes.

## Tried and abandoned
none

## Known risks
- Install on Linux not yet proven. A later bump of a package in CONSTRAINTS fails the locked test until a row is added (test_author work).
- Local env: a site-packages `tests` package shadows the repo's `tests` dir, so `pytest tests/test_lock_consistency.py` fails at collection locally. I ran it with a temporary empty tests/__init__.py (removed after). Not a repo change.

## Next step
Owner pushes. After merge (or on the branch): dispatch weekly-scripts (requirements-generate.txt) and render.yml (requirements-render.txt). Mark p4c-lock-pin done with this task (superseded). Optional hand-requested security review (supply-chain lock).

## Docs
none

## Evidence
- tests/test_lock_consistency.py + tests/test_render_lock.py: 16 passed (with the temporary __init__.py).
- ruff check .: passed. python tests/docs_check.py: passed.
- mypy and full pytest not run (no pipeline code changed).
