# Handoff: p4-daily-workflow (implementer)

## Goal
Write `.github/workflows/daily_publish.yml` (PRD R16, Workflow B): render, claim, upload and record jobs, so no job holds both a secret and a write token.

## Status
partial: awaiting CI. The structure tests pass locally. The claim and record shell tests (`@shell_tools`) skip on Windows and jq is not installed here, so they have not run. They must pass in CI before this counts as done. actionlint is not installed locally either, so the workflow has not been linted; CI's actionlint step is the check. Security review applies (`.github/workflows/**`).

## Round 1
Review found the ledger could record a script version that was never rendered or uploaded (render read `github.sha`, claim and record read main). Fixed in `daily_publish.yml` only:
- `render`: job-level `if: github.ref == 'refs/heads/main'`; `pick` step also outputs `script_blob` (`git hash-object` of the script, checked against `^[0-9a-f]{40}$`).
- `claim`: takes `SCRIPT_BLOB` through env, validates it, refuses when main's script hash differs, before the first push and again after the `pull --rebase` retry. `script_sha` is written from `SCRIPT_BLOB`.
- `upload`: re-hashes the script in its own checkout and refuses on a mismatch before the CLI runs.
- `record`: before moving the script, its hash must equal the record's `script_sha`, else fail and leave the claim.
- Blocker: the locked claim shell tests pass no `render.script_blob`, so they will fail in CI against the strict claim. `CONTRACT_CHANGE.md` written with the test changes needed. The architect must update the tests; the workflow was not loosened.
- Owner notes for the runbook (R17): a stuck claim with no upload step log means nothing was sent; the YOUTUBE_* secrets must be environment secrets with a main-only deployment rule. A manual dispatch from a branch now skips every job.
- Still partial: the shell tests and actionlint run in CI only. Awaiting CI.

## What changed (and why)
- New file `.github/workflows/daily_publish.yml` only.
- Triggers: schedule `7 14 * * *` and `workflow_dispatch` (no inputs). Workflow-level concurrency group `daily-publish`, no cancel. Read-only token at workflow level.
- `render`: no secret, read token, checkout without credentials. Same heavy install as `render.yml` (torch from the CPU index first, model cache keyed on the heavy pins and constants). `pick` prints the id, the step regex-checks it and writes `script_id` to the job output. `render_one` renders from `queue/approved/$SCRIPT_ID.json`. Only `out/render/final.mp4` goes up as an artifact, retention 1 day.
- `claim`: `contents: write`, no secret, runs no repo code. Checkout `ref: main` with credentials. Git hooks are off through `GIT_CONFIG_COUNT/KEY_0/VALUE_0` (same as `weekly_scripts.yml` open-pr). It re-checks the id, refuses when main already holds the record or its script hash differs from `SCRIPT_BLOB`, writes the record with `jq` (`script_sha` from `SCRIPT_BLOB`), commits and pushes. On a rejected push: one `pull --rebase`, a second hash check, one more push.
- `upload`: read token, `environment: youtube` (O1 option b), checkout without credentials, hashed install of `requirements-generate.txt` only, no `setup-python` cache and no `actions/cache` step. The artifact downloads to `runner.temp/artifact`, never over the checkout. The one step with the three YOUTUBE_* secrets re-checks the id and runs `python -m pipeline.publish.youtube SCRIPT MP4 "$GITHUB_OUTPUT"`. The job outputs `video_id` and `sent` from that step.
- `record`: `if: always() && needs.claim.result == 'success'`, `contents: write`, no secret. It needs a claim-only record on main (else it fails and pushes nothing). With a valid video id: sets `youtube_video_id` and `published_at`, `git mv` the script to `queue/published/` unchanged, one commit. With `sent=false` and no video id: `git rm` the record, one commit, exit 0. Anything else fails and leaves the claim.
- Every job-output value (`script_id`, `video_id`, `sent`) reaches `run:` through `env:` only. No `${{ }}` sits inside any `run:`.

## Decisions made
- A missing `video_id` and a missing `sent` line both fall into the last branch of `record`: the claim stays and the run fails. In effect a missing `sent` means `sent=true`, which is the safe side (the owner checks the channel).
- A non-empty but malformed `video_id` also fails and keeps the claim, even when `sent=false`. A video id that does not match `^[A-Za-z0-9_-]{11}$` is never trusted.
- No `actions/cache` and no `cache:` on `setup-python` in `upload`, since that job holds the secrets and the locked test forbids it. `render` keeps both.
- The upload step re-checks the script id with the same regex as `claim` and `record`, because that path is built from a job output in the job that holds the tokens.
- The upload CLI's output lines are not re-validated in a separate step. `record` regex-checks the id before using it, and the CLI itself only writes an id that matched the pattern.
- The artifact name is `final-video`, since `render.yml` already uses `render` for its own artifact (not a conflict across workflows, but the names stay distinct).

## Tried and abandoned
none

## Known risks
- The shell tests have not run locally (Windows, no jq). If one fails in CI the cause is likely quoting or the `jq` filter in the claim or record step.
- Artifact layout: with a single-file `path`, `upload-artifact` stores `final.mp4` at the artifact root, so the upload step reads `$RUNNER_TEMP/artifact/final.mp4`. Not run on GitHub yet. If the layout differs, the upload fails with `sent=false`, the claim is released and the run is red. The first manual run (R17) is the real check.
- The `youtube` environment must exist in the repo settings, with the three secrets stored there as environment secrets and a main-only deployment rule. Without it the upload job waits or fails.
- A `record` push failure after a good upload leaves the claim in place, by design (plan).
- Pushes with `github.token` start no CI run, so the ledger commits are not checked until the next PR touches main.

## Next step
1. CI on a draft PR: confirm the shell tests, `make check` and actionlint pass.
2. Security review, then Gate 2.
3. Owner: create the `youtube` environment and add the secrets (plan Phase 0 step 6), then dispatch the workflow by hand for the first live run (R17).

## Docs
- Applied here: none (`paths_allowed` is the one workflow file).
- Owed at Phase 4 close-out: architecture.md section 1b for Workflow B (four jobs, claim before upload, outputs through env); workflow.md status row for p4-daily-workflow; CLAUDE.md Status "Next" line; spec.md note that the upload job installs `requirements-generate.txt` only.
- Owner setup note (for PRD R17 or the runbook): the `youtube` environment, its three secrets and its main-only deployment rule.
- lessons.md: no new entry; nothing went wrong.

## Evidence
Run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe` (the system `tests` package shadows the repo's, lessons.md 2026-11-15).
- `LOOM_TASK=p4-daily-workflow pytest tests/test_daily_publish_workflow.py tests/test_workflow_safety.py`: 57 passed, 24 skipped (the shell tests, Windows).
- Full `pytest -q`: 1465 passed, 54 skipped. `ruff check .`: passed. mypy not run (no pipeline code changed).
- Not run: the claim and record shell tests, actionlint, `make check`. Awaiting CI.
- `git status`: only `.github/workflows/daily_publish.yml` and this handoff changed.
