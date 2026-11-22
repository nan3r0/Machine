# Handoff: p4b-pick-ledger

## Goal
Pick skips scripts that already have a publish record instead of raising (plan P1-2).

## Status
done

## What changed (and why)
`pipeline/publish/pick.py`: rule 2 (published script still in `queue/approved/` raises) is removed. The candidate filter now also drops any script_id that has a record. Rule 1 (claim-only record stops the run) is unchanged, so a script with a record always has a video id by the time it is skipped. Module and `next_script` docstrings updated: rules list, and the records folder is the ledger branch's `data/published/` checked out by the workflow. CLI unchanged.

## Decisions made
Merged the skip into the existing `due` comprehension rather than adding a separate loop (smallest diff).

## Tried and abandoned
none

## Known risks
Approved scripts stay in `queue/approved/` after publishing, so the queue folder keeps growing until something moves them. Out of scope here.

## Next step
Gate 2 review and the security specialist review (`pipeline/publish/**` trigger), then merge.

## Docs
Any doc that describes pick rule 2 as an error (PLAN.md section 7 Workflow B, spec.md, architecture.md, PRD R14 wording) should say a recorded script is skipped. No file deletions needed.

## Evidence
`pytest -q tests/publish/test_pick_ledger.py tests/publish/test_pick.py`: 29 passed. `ruff check .`: clean. `mypy --strict pipeline/`: no issues in 25 files.
