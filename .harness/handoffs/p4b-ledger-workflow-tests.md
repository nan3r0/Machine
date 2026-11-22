# Handoff: p4b-ledger-workflow-tests (test_author)

## Goal
Locked tests for Workflow B on the bot-only `ledger` branch (CSO P1-2, P4-1, P4-2; QA lead rank 3), per the job-by-job spec in `.harness/handoffs/p4b-plan.md`, "P1-2 design". Trim `tests/test_daily_publish_workflow.py` to tests that hold for both the current and the ledger workflow.

## Status
partial, awaiting CI. All edits are committed; the task is done once the Linux CI runs in Next step are as expected. The shell tests have never run: they skip on Windows, and the new file skips until p4b-ledger-workflow is done or is LOOM_TASK. The new file is locked by the `tests/**` glob in `.harness/locks.yaml`.

## What changed (and why)
- New `tests/test_daily_publish_ledger.py` (owned by p4b-ledger-workflow, so it skips on main until that task is done).
  - Structure: render checks out `ledger` at `ledger` without credentials and runs `pick queue ledger/data/published`; claim has main at the root (`ref: main`, no credentials) and the ledger at `ledger` with credentials; upload has main (`ref: main`) and the ledger at `ledger`, both without credentials, and the step named "Require this run's claim..." comes before the only secret step; record checks out only `ledger`, with credentials (any path). Only claim and record push, and every push line names `ledger` and not `main`. No `github.run_id` or `github.run_attempt` expression anywhere and no step env key starting `GITHUB_`; claim and the upload guard read `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT`, record reads `GITHUB_RUN_ID`.
  - Shell harness: the workspace is built from the job's own checkout steps (ref, path, credentials) against a bare remote seeded with `main` and an orphan `ledger` independently of the workflow (lessons.md 2026-11-22). A checkout without credentials gets an unusable push URL. Steps run as GitHub does (`bash -e`, or pipefail flags under `shell: bash`), honour `working-directory`, and get a clean `GITHUB_*`/`RUNNER_*` environment (inherited CI values stripped).
  - claim: writes the record with run id and attempt from the environment as JSON numbers, one ledger commit, main untouched; refuses an existing record (claim-only, published, other run), an edited or removed script on main, bad ids, bad blobs and non-numeric run ids or attempts; one rejected push retries after an unrelated ledger commit; a concurrent claim of the same script makes it fail with the other claim kept.
  - upload guard: runs the steps from the guard through the secret step with fake `python`, `python3`, `pip`, `pip3` on PATH. A good claim calls exactly `python -m pipeline.publish.youtube queue/approved/<id>.json <RUNNER_TEMP>/artifact/final.mp4 <GITHUB_OUTPUT>`. No record, a published record, another `script_sha`, another `run_id`, another attempt (re-run), a symlinked record, `../x`, `x;touch pwned` and a main blob mismatch all exit non-zero with no fake called.
  - record: fills the video id and `published_at` in one ledger commit with the other fields unchanged, also when only the attempt differs (re-run of record); main and `queue/approved/` untouched; `sent=false` deletes the claim; unknown outcomes keep it; no record, a published record or another run's claim are refused for both outcomes; bad ids refused. No git hook runs in claim or record.
- `tests/test_daily_publish_workflow.py`: deleted every shell test and helper (all built the ledger on main). `test_render_job` now checks `pick queue ` only. `test_write_jobs_run_no_pipeline_code` dropped the single `ref: main` checkout check, matches pushes with a regex (`git -C ledger push` counts), and now checks structurally that every claim or record step calling git sets `core.hooksPath=/dev/null` through `GIT_CONFIG_*` env (the behavioural hooks test moved to the new file). Docstrings rewritten to hold for both layouts.
- `workflow.md`: R16 row lists tests/test_daily_publish_ledger.py in plain text.
- `tests/workflow_rules.py`: unchanged. claim and record keep `contents: write` only, and the allowlists do not depend on checkouts or branches.

## Decisions made
- record's checkout path is free (root or `ledger`); the task fixes only that it is the ledger alone. The harness places it where the YAML says.
- claim's root checkout must name `ref: main`, like upload: the blob check is about main's current version, not the run's commit.
- The upload guard range is from the "Require this run's claim" step through the secret step, so a blob check split into its own step still runs in the test.
- Run ids tested with clearly non-numeric values only; `0` and leading zeros are left unlocked.
- The expected blob is computed with hashlib, not by git on the remote, so seeds and expected values do not come from the code under test.

## Tried and abandoned
none

## Known risks
- The shell harness has never executed (Windows skips it). First real run: Linux CI. With LOOM_TASK unset the new file skips. With `LOOM_TASK=p4b-ledger-workflow`, against today's workflow:
  - Expected to fail: the six structure tests (so `test_acceptance` too), claim success, claim retry, claim against a concurrent claim, claim when the ledger holds a record, the claim run-number cases, upload success, record complete (both), record release, and the record hooks case.
  - Expected to pass trivially (today's workflow finds nothing under `ledger/`): the other refusal cases and the claim hooks case.
  - A test bug, to fix before the implementer starts: any setup error, such as a `CalledProcessError` from git in `seeded`, `workspace` or `change`, or a `ValueError` from unpacking.
- The old file's hooks check requires hooks off through `GIT_CONFIG_*` step env, as today. A ledger workflow that turns hooks off another way (`git -c core.hooksPath=...`) would fail it; the plan says "as today", so the implementer should keep the env form.
- During the window before p4b-ledger-workflow merges, nothing on main runs the claim and record steps under bash (the old shell tests are gone, the new ones skip). Accepted in the plan's coverage window; `daily-publish` is disabled.

## Next step
Orchestrator: push on a `docs/*` branch, open the PR, and check the Linux CI run is green (new file skipped). Then one CI run with `LOOM_TASK=p4b-ledger-workflow`: only new-file tests fail, and exactly the ones listed under Known risks. Then p4b-ledger-workflow can start.

## Docs
- workflow.md R16 row: done in this task.
- None else. PRD R16.3 wording is p4b-docs's job.

## Evidence
- `.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_daily_publish_workflow.py tests/test_daily_publish_ledger.py tests/test_docs_check.py tests/test_workflow_safety.py`: 90 passed, 69 skipped.
- `.venv/Scripts/python.exe -m pytest -q --tb=short`: 1466 passed, 123 skipped.
- `.venv/Scripts/python.exe -m ruff check .`: all checks passed.
- `.venv/Scripts/python.exe -m mypy --strict pipeline/`: no issues in 25 files.
