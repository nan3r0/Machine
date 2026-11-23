# Handoff: p4b-cso

## Goal
Threat model version 3.1 after the ledger branch, run binding, render lock and token check (phase review T11), with every claim checked against merged `main` (#140) by file:line.

## Status
done. Version 3.1 written; docs check passed. Owner sign-off of v3.1 is pending and is an R18 gate.

## What changed (and why)
- Header: version 3.1, dated 2026-11-23, sign-off pending. Every line reference was checked again, including the rows carried from version 2 and 3. `daily_publish.yml`, `youtube.py`, `pick.py` and the workflow tests all moved.
- Section 1: there are five workflows now (`weekly_audit.yml` added). Workflow B is described on the `ledger` branch, and `record` no longer moves scripts.
- Section 2: "(re-check on Google's pages at audit)" became "confirmed 2026-11-22 (p4-audit)". The ledger asset now names the branch, and there are 14 sources.
- Section 3: new boundary 10, the `ledger` branch into Workflow B. The public is now boundary 11.
- 4.2: P1-4 heavy half is rated Mitigated with residuals (P4b-1) and stays a go-live gate until the Linux proof is recorded. New rows for the pip cache seeded by unhashed installs and for the weekly audit's unhashed install.
- 4.3: new row for the access token character check (`youtube.py:27`, `:150-153`).
- 4.4: P1-2's repo half is mitigated (only `claim` and `record` push, and only to `ledger`). The rest is marked Owner setting.
- 4.8: P4-1 and P4-2 are closed, with tests cited.
- 4.9 (new): rows for the ledger branch. They cover who can push, a deleted completed record, a forged record, symlinked records and parent folders, a missing branch, and code execution in write jobs.
- Sections 6 and 7: the ranking is updated. The owner checklist gains the ledger bootstrap, both rulesets, deny rules for `ledger` pushes, F8 retention, keeping `daily-publish` disabled, and the render lock Linux proof.

## Decisions made
- P1-4 is not marked closed. The p4b-render-lock handoff is still `partial` and records no green `render.yml` run. The two sdists build with an unhashed backend.
- P1-2 stays Critical in section 6 until the owner settings are on, because the orchestrator state says they are not.
- Owner settings are marked "Owner setting", not "Mitigated" (per the task note).

## Tried and abandoned
none

## Known risks
- Not verified live: `run_attempt` increments on "re-run failed jobs" (only GitHub's docs, as quoted in p4b-plan). The `youtube` environment rule and the rulesets are not visible from the repo.
- A symlinked parent folder under `ledger/data/` is untested. Reading the code, it should fail closed.

## Next step
Orchestrator: create `docs/p4b-cso` from current origin/main, commit `docs/threat-model.md` and this handoff, run `python tests/docs_check.py`, and open the PR. Owner: sign off v3.1 before go-live.

Proposed tasks (non-blocking findings, none critical or high):
1. **P4b-1 (low, implementer on the render locks):** build the two sdists without unhashed code. Either pin and hash setuptools and wheel and add `--no-build-isolation` to the second render install, or ship hashed prebuilt wheels. Check it with a `render.yml` dispatch. Do this at the next lock regeneration.
2. **Render lock proof (owner, go-live gate):** record a green `render.yml` run on Linux with QA passed, then mark p4b-render-lock done.
3. **Runbook (p4b-runbook, scribe):** only claim-only records may be deleted from `ledger`, never one with a video id, because scripts stay in `queue/approved/` and a deleted record republishes.
4. **Optional (test_author, low):** a test that a symlinked `ledger/data/published` folder fails closed in `claim` and `record`.

## Docs
- Applied: `docs/threat-model.md` version 3.1.
- Owed (p4b-docs or close-out):
  - CLAUDE.md Status: threat model v3.1 sign-off pending.
  - workflow.md: a p4b-cso row in the Phase 4 status table once done.

## Evidence
- Read: the task YAML, p4b-plan, p4-cso, the previous threat model, `daily_publish.yml`, `render.yml`, `weekly_audit.yml`, `youtube.py`, `pick.py`, `tests/workflow_rules.py`, `tests/test_daily_publish_workflow.py`, `tests/test_daily_publish_ledger.py` (structure and :76-143), `tests/docs_check.py`, `locks.yaml`, the render lock files and handoff, and the orchestrator state.
- Grep checks: the ci.yml and weekly_scripts.yml lines cited, `test_workflow_safety.py:272`, `test_youtube_placement.py:99-111`, and the sources count (14).
- Not run (no shell in this session): `python tests/docs_check.py`, git fetch, merge, branch and commit.
- No em dashes in either file.
