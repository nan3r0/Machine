# p4b-ledger-workflow

## Goal
Workflow B writes its claim and record to the bot-only `ledger` branch, bound to the run id and attempt (CSO P1-2, P4-1; plan section "P1-2 design").

## Status
Partial: awaiting CI. The structure tests pass locally (63 passed). The 62 shell tests skip on Windows, so only Linux CI proves them.

## What changed (and why)
Only `.github/workflows/daily_publish.yml`.
- render: second checkout of `ledger` at `ledger/`, no credentials. Pick reads `ledger/data/published`.
- claim: main at the root without credentials (blob check), `ledger` at `ledger/` with credentials. It checks `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` against `^[1-9][0-9]*$`. It refuses when the ledger holds a record or a symlink for the script, or when main's script blob differs. It writes the record with `run_id` and `run_attempt` through `jq --argjson`, commits in `ledger/` and pushes to `ledger`. One rejected push gets one `pull --rebase` and one retry. A same-script claim from another run conflicts in the rebase and fails the step.
- upload: main and `ledger/`, both without credentials. The claim check refuses a missing or symlinked record and anything except: video id null, `script_sha` equal to the blob, `run_id` and `run_attempt` equal to this run's. It is still the step before the secret step. No `sent=false` from the guards.
- record: ledger only, with credentials. It requires a claim-only record with this run's `run_id` (not the attempt, as in the plan). A video id fills in the record and commits it. `sent=false` removes the claim. Anything else keeps the claim and fails. Nothing touches main, and the `queue/published` move is gone.
- Comments updated to match.

## Decisions made
- Dropped the old main re-check after `pull --rebase` in claim: pulling the ledger cannot change main.
- Dropped the script-blob check in record: the script no longer moves, and upload checks it before sending.
- Record rejects a symlinked record too (same rule as upload).

## Tried and abandoned
none

## Known risks
- Shell tests were traced by hand, not run. If CI shows a failure, look first at `git clone` into a nonexistent root with no `path` (the record job), and at the rebase-conflict path in claim.
- The orphan `ledger` branch must exist before the first run, or the render checkout fails (closed). Owner or orchestrator bootstrap, per the plan.
- The `main` ruleset must be turned on only after this merges.
- Security specialist review is due (workflow trigger).

## Next step
Open a draft PR so CI runs the shell tests, then Gate 2 and the security review. Then the ledger bootstrap and the rulesets (owner).

## Docs
- PRD.md R14.1, R16.3, R17 and R18 wording is in the plan's "Proposed PRD wording" (p4b-docs applies it).
- architecture.md and spec.md: Workflow B claim and record live on the `ledger` branch, not `data/published` on main, and `queue/published` is no longer written (p4b-docs).
- CLAUDE.md Status: add p4b-ledger-workflow as built, awaiting CI.
- docs/runbook.md: the ledger bootstrap and what a red claim or record job means (p4b-runbook).

## Evidence
- `pytest -q --tb=short tests/test_daily_publish_ledger.py tests/test_daily_publish_workflow.py tests/test_workflow_safety.py`: 63 passed, 62 skipped (shell tests, Windows).
- `ruff check .`: clean. `mypy --strict pipeline/`: clean.
