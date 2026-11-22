# Handoff: p4-cso

## Goal
Threat model version 3 for Phase 4 (YouTube publishing, the OAuth token, bot commits to main), with file:line controls checked against the code.

## Status
done. Only `docs/threat-model.md` changed. Owner sign-off of version 3 is pending and is a go-live gate. Section 7 of the doc lists 7 settings outside the repo the owner must confirm.

## What changed (and why)
- Added rows: P1-4 heavy half (render job installs unhashed, so `final.mp4` can be altered; upload checks size only), public upload logs (stderr carries up to 200 characters of Google's response body, secrets redacted first), agent sessions able to dispatch or re-run `daily-publish`, a new section 4.8 for the Workflow B publish path, a new section 4.9 for the public repo, and a section 7 owner checklist.
- Changed rows: scope and assets (public repo, YouTube secrets, derived token, quota, minutes budget), hashed installs now cover both secret jobs, WRITE_JOBS and SECRET_JOBS rows include Workflow B, P1-1 YouTube part covered by the main-only deployment rule on the `youtube` environment (owner setting), P1-2 raised to critical (anything pushed to main reaches the token at the next run).
- Closed: P1-5, repudiation through `script_sha`, official API only, nothing published in artifacts or logs.

## Decisions made
- The upload checkout of `main` plus the claim pre-check counts as mitigated. Re-running failed jobs after an unknown upload outcome stays a separate gap (P4-1).
- Settings outside the repo are marked "Owner setting", not "Mitigated".

## Tried and abandoned
none

## Known risks
Rows carried over from version 2 keep their version 2 line references. Unverified: GitHub ruleset bypass rules, `run_attempt` on a re-run of failed jobs, whether `youtube.upload` can call `videos.update` or `videos.delete` (the audit should re-check).

## Next step
Proposed tasks, in order:
1. P4-2 (low, test_author): locked test for the upload job's `ref: main` checkout and the "Require this run's claim on main" step, running before the secret step.
2. P4-1 (medium, go-live gate): claim records `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT`, upload refuses unless both match; plus a locked test and an owner deny rule on agent `gh run rerun`. Trade-off: a re-run after an upload failure becomes a manual reconcile.
3. P1-4 heavy half (high, go-live gate): hash-checked lock for the render job (needs an owner-approved lock tool, spec.md section 7).
4. P1-2 (critical, go-live gate): ruleset on `main` requiring a PR and the `check` job, agent deny rules for `git push` to main, `gh pr merge`, `gh run rerun`, `gh workflow run daily-publish`. Recommend no bot bypass and a bot-only ledger branch (Architect task; `pick` and `record` change).
5. Runbook (docs): kept claim handling, token revoke and rotate.

## Docs
- Applied: `docs/threat-model.md` version 3.
- Owed at close-out: `architecture.md:123` still says "private repo on a free plan has no branch protection"; CLAUDE.md Status still says "Repo: private" and that the threat model is signed off (that was v2); add the owner gate "threat model v3 sign-off".

## Evidence
Docs-only change, no tests run. No em or en dashes in the file. Rows checked against `daily_publish.yml`, `youtube.py`, `pick.py`, `workflow_rules.py`, `test_daily_publish_workflow.py`, `ci.yml`, `constants.py`.
