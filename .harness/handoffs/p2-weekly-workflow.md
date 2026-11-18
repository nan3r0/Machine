# Handoff: p2-weekly-workflow

## Goal
Add `.github/workflows/weekly_scripts.yml` (Workflow A): Sunday 06:00 UTC and manual dispatch, generate the weekly scripts, open a PR with them.

## Status
done for the automated checks. Manual acceptance (dispatch, PR with 7 scripts, flags readable on mobile) waits for owner decision D1 and the `GEMINI_API_KEY` repo secret. actionlint is not installed locally; CI runs it in `make check`.

## What changed (and why)
- New `.github/workflows/weekly_scripts.yml`, workflow permissions `contents: read`.
- Job `generate` (read-only token): checkout without credentials, Python 3.12, `requirements.txt` only, one step runs `python -m pipeline.script.batch sources queue out/batch` with `GEMINI_API_KEY` in that step's env, then uploads `queue/approved/` and `out/batch/pr_body.md` (retention 3 days, fails if nothing to upload).
- Job `open-pr` (`contents: write`, `pull-requests: write`, needs `generate`): the only checkout that keeps credentials, downloads the artifact, creates `scripts/<UTC date>`, commits `queue/approved/*.json`, pushes, runs `gh pr create --body-file`. `GH_TOKEN` comes from `env:` on that step, not from the run text. No secret and no pipeline code in this job.
- Branch name and PR title come from the date only. No `${{ }}` inside any `run:`.

## Decisions made
- `download-artifact` is not used in ci.yml, so it had no pin to copy. I resolved `actions/download-artifact` v8.0.2 with `gh api` (the tag points straight at a commit) and pinned `9000827ccba6bdab643e8b6fd33ac0654aef8333`. The other three pins are copied from ci.yml.
- Artifact upload of two paths keeps the repo-relative layout, so download into `.` restores `queue/approved/` and `out/batch/pr_body.md`.
- Commit identity is the `github-actions[bot]` noreply address (no personal details).
- Timeouts: 30 min for generate, 10 min for open-pr.

## Tried and abandoned
- First draft pinned download-artifact from memory (`3e5f45b...`). That SHA was unverified, so I replaced it with the one resolved from the GitHub API.

## Known risks
- Two runs on the same UTC day make the same branch name, so the second push fails. Fine for weekly plus one manual dispatch; add the run id to the branch name if it becomes a problem (the task says the name comes from the date).
- The artifact contains all of `queue/approved/` including files already committed; `git add queue/approved/*.json` stages only the new or changed ones. If the batch wrote nothing new the commit step fails loudly (batch exits 1 first in that case).
- Not run on GitHub yet. Pushes and PRs made with the default token start no `ci.yml` run, as the task notes.

## Next step
Gate 2 and security review. Owner decides D1 and adds the secret, then dispatches the workflow for manual acceptance.

## Docs
- `CLAUDE.md` Status: move p2-weekly-workflow from "Next" to done in Phase 2.
- `workflow.md`: mark p2-weekly-workflow done in the status table (acceptance pending the manual step).
- `architecture.md`: if it describes Workflow A, name the `generate` / `open-pr` split and that `download-artifact` is now an approved action in use.
- `spec.md` section 7: if it lists approved actions, add `actions/download-artifact` (pinned v8.0.2).
- `lessons.md`: no new entry.

## Evidence
- `LOOM_TASK=p2-weekly-workflow .venv/Scripts/python.exe -m pytest tests/test_weekly_workflow.py tests/test_workflow_safety.py -q`: 39 passed.
- Full suite `pytest -q`: 724 passed, 14 skipped (heavy, CI only).
