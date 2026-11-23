# Handoff: p4b-runbook
## Goal
Write `docs/runbook.md`, the owner's plain-English runbook for Workflow B (daily publish), from the content list in `.harness/handoffs/p4b-plan.md`.
## Status
done
## What changed
- `docs/runbook.md`: new file with the five sections from the plan (one-time setup, red run, kept claim, token revoke and rotate, refill). Every job name, message and file path is taken from `.github/workflows/daily_publish.yml` (worktree copy at 8ef70f6), plus the `pick` error texts in `pipeline/publish/pick.py`.
- `.harness/handoffs/p4b-runbook.md`: this handoff.
- Not committed. No branch created, nothing pushed. The shell was not available in this session, so git and the docs check did not run (see Evidence).
## Decisions made (and why)
- Kept the plan's wording for the re-run rule. Section 3 says never re-run failed jobs while a claim is kept, then names one exception: re-run only the record job after a successful upload whose record push failed. The plan states both, and the workflow comment at the record job describes the same recovery.
- Step 4 (token rotate) follows the plan, and adds "reset the client secret if it may have leaked" from the threat model's "On any doubt" item 7.
- Nothing about the ledger branch's name or bot identity beyond what the workflow shows.
## Tried and abandoned
- none
## Known risks / fragile spots
- Not verified against live origin/main. The shell tools were missing, so no fetch or merge ran. Check the workflow file and `pipeline/publish/pick.py` on main before merging, since the pick messages quoted here come from the worktree copy. The plan's p4b-pick-ledger changes rule 1 and the messages, so the "unconfirmed claim for" line may change.
- Conflict for the owner: `.harness/handoffs/p4b-plan.md` says "a re-run of only record is safe", and the CSO threat model item 7 says "never re-run failed jobs". The runbook follows the plan and labels the exception. Owner or Architect to confirm.
- Step 1 setup items (environment rules, rulesets, deny rules, failure emails, retention, consent screen) are owner settings. The runbook gives menu paths from memory of the GitHub and Google UIs. The owner should check them against the live screens.
- Step 5 (refill) numbers come from the plan: 7 a week, about 14 sources every second weekend. Reviewed by the owner on 2026-11-22 per the plan.
## Next step for whoever picks this up
- Finish in a shell: `git fetch`, `git merge origin/main`, `git checkout -b docs/p4b-runbook` (the uncommitted files come along), then `python tests/docs_check.py`.
- Check the runbook against the merged workflow and pick.py, then commit with the trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Do not push.
- Set this handoff's status to `done` once committed.
- Orchestrator: decide the re-run conflict above.
## Docs
- none
## Evidence
- tests: not run. `python tests/docs_check.py` not run (no shell in this session).
- commands run: none. Read and Grep only: `.harness/tasks/phase4b/12_runbook.yaml`, `.github/workflows/daily_publish.yml`, `.harness/handoffs/p4b-plan.md`, `.harness/handoffs/p4-plan.md`, `docs/threat-model.md`, `pipeline/publish/pick.py`, `tests/docs_check.py`, `HARNESS.md` section 7.
- Checks by hand: no em dashes and no personal details or secret values in `docs/runbook.md` (grep clean).
