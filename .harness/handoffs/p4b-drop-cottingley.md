# Handoff: p4b-drop-cottingley (test_author)

## Goal
Drop the Cottingley Fairies source (audit F6, owner decision 2026-11-22: the story names two children) before the owner's first manual weekly-scripts run (R13.5).

## Status
done. Committed on `docs/p4b-drop-cottingley` (worktree `.claude/worktrees/p4b-drop-cottingley`, locked test on a `docs/*` branch per lessons.md 2026-11-18), not pushed. Linux CI starts with the PR.

## What changed (and why)
- `sources/cottingley-fairies.yaml`: deleted (fact ids 501 to 508).
- `tests/test_sources_files.py`: `MIN_FILES` 15 becomes 14; its comment now says 13 seeded mysteries plus the Bloop source; the `test_acceptance` docstring says "at least 14". PRD R8.2 ("at least 14 sources") still holds.

## Decisions made
- Checked first that no queued script cites the source: `queue/` holds only `queue/approved/sample-65s.json`, and it cites none of the ids 501 to 508 and does not name Cottingley.
- Fact ids 501 to 508 are now free. Nothing reuses them, and nothing needs to.

## Tried and abandoned
none

## Known risks
- None for the pipeline: the weekly batch loads whatever is in `sources/`, and the used-source ledger (D3) never recorded Cottingley because Workflow A has not run yet.
- None for tests: the 63 local skips are the existing heavy and Linux-only tests, none of which reads `sources/`.

## Next step
Gate 2 review, then merge before the owner's first weekly-scripts run (R13.5).

## Docs
- Applied: none (both docs files are outside `paths_allowed`).
- Owed (p4b-docs, already in the p4b-plan "Docs owed" list):
  - architecture.md:141 says 14 sources; that is true again now.
  - PRD.md:218 sources count: 14 (13 mysteries plus the Bloop).
  - PRD.md section 7: F6 decision (Cottingley dropped, 2026-11-22).
  - CLAUDE.md:21 Status says "seeded sources (15 files)"; it is 14 now.
  - docs/threat-model.md:41 says "15 files"; it is 14 now (p4b-cso, not in the plan's list).
  - p4-plan's "the 15 sources last about 2 weeks" is history; no change.
- lessons.md: no new mistake.

## Evidence
- `grep -ri cottingley`: only handoffs, the task YAML and the deleted source matched. No code or test references it.
- `grep 50[1-8] queue/`: no match.
- `python -m pytest -q --tb=short tests/test_sources_files.py`: 7 passed.
- `ruff check tests/test_sources_files.py`: passed.
- `python tests/docs_check.py`: passed.
- With `.claude/worktrees/p2b-qa-tests-batch/.venv` (the global Python 3.11 has a stray `tests` package in site-packages that shadows the repo's, so use that venv):
  - `pytest -q tests`: 1465 passed, 63 skipped (same counts as main in p4b-plan).
  - `pytest -q .harness/tests`: 88 passed.
  - `ruff check .`: passed.
- `grep` for stale "15 sources/files" in `*.md`: results are in the Docs section.
