# Handoff: p4-pick

## Goal
Implement `pipeline/publish/pick.py` (PRD R14): pick the oldest due approved script with no ledger record, and refuse when a claim has no video id.

## Status
done

## What changed (and why)
- `pipeline/publish/pick.py`: `next_script` and the CLI `main`, replacing the stubs.
  - Loads every `data/published/*.json` as a `PublishRecord` and every `queue/approved/*.json` as a `Script`. A file that does not parse, or a record whose file name is not `<script_id>.json`, raises `PickError` naming the file.
  - A missing records folder raises `PickError`; a missing `approved` folder counts as empty.
  - Rule order: a record with no video id raises (nothing is picked, even if other scripts are due); a recorded script still in `approved/` raises; then the first due script by (`publish_after`, `id`), or `PickError("queue empty: ...")`.
  - The CLI takes today's UTC date, prints only the id on success, and prints the reason to stderr with exit 1 on `PickError`.

## Decisions made
- Two small private loaders (`_load_records`, `_load_approved`) instead of one generic one, because the error wording and the extra file-name check differ.
- Parse errors are caught as `(OSError, ValueError)`: pydantic's `ValidationError`, including invalid JSON, is a `ValueError`. This is a real boundary (files on disk), not a swallowed error.
- The queue-empty message is "queue empty: no approved script is due" (the locked tests only need the prefix).

## Tried and abandoned
none

## Known risks
- A script file whose name does not match its `id` is not rejected. The task and tests do not ask for it; the ledger and the approved check both use `script.id`.
- Reads every approved script on each run. Fine at the queue's size (a few dozen files).

## Next step
p4-youtube and p4-daily-workflow can use `python -m pipeline.publish.pick queue data/published` and regex-check the single line it prints.

## Docs
none. No doc is made false by this change. At Phase 4 close-out the existing owed items (architecture.md section 1b, spec.md layout) already cover the pick step.

## Evidence
Run with a sibling task venv, because an installed `tests` package shadows the repo's `tests/` (lessons.md 2026-11-15; plain `python -m pytest` failed at collection with `No module named 'tests.script'`).
- `LOOM_TASK=p4-pick pytest tests/publish/test_pick.py -q --no-cov`: 15 passed, including `test_acceptance`.
- `ruff check pipeline/publish/pick.py`: passed.
- `mypy --strict pipeline/publish/pick.py`: passed.
- Full suite not run (only this one module changed); CI runs it on the PR.
