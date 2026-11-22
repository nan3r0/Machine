# Handoff: p2d-ci-triggers (Test Author)

## Goal
Stop ci.yml from spending the Actions allowance twice per push (CSO P1-5): the check runs once per PR update and once per push to main, superseded PR runs are cancelled. Plan: `.harness/handoffs/p4-plan.md`, part A.

## Status
partial, "awaiting CI" (Test Author, locked file only). The code is complete and the locked tests pass locally, but actionlint has not run on it and the new triggers have not run on GitHub. Committed on `task/p2d-ci-triggers`, not pushed. The repo is public since 2026-11-21 (O1), so standard runners do not draw on the allowance: the owner can push and open a draft PR now.

## What changed (and why)
`.github/workflows/ci.yml`, top only:
- `push` is limited to `branches: [main, "scripts/**"]`. Task and docs branches now get CI only from their PR event, which removes the duplicate push run. `scripts/**` stays on push because Workflow A opens that PR with GITHUB_TOKEN, whose `pull_request` runs wait for approval, and the owner's mobile edits there must still be checked (R12.3).
- `pull_request` keeps no filter and `workflow_dispatch` stays.
- New workflow-level `concurrency`: group `ci-${{ github.event.pull_request.number || github.run_id }}`, `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. A PR's runs share a group and a newer update cancels the older run. Every other run (main push, scripts push, dispatch) has its own group, so GitHub's pending-run replacement can never drop a queued reports dispatch or a main run.
- Two short comments explain the why of each block. Everything below `permissions` is unchanged byte for byte (pinned actions, env, fetch-depth, scope check, docs check, LOOM_TASK step, reports job and its `if`).

## Decisions made
- Concurrency sits at workflow level, as the task says, so the reports job is covered by the same run-id group as its dispatch.
- No `paths-ignore`, no new steps, no new caches (per the task and p4-plan "Not done").

## Tried and abandoned
- Running pytest with the system Python: the stray site-packages `tests` package shadows the repo's (lessons.md 2026-11-15), even with `PYTHONPATH=.`. Used `../p2b-qa-tests-batch/.venv/Scripts/python.exe`.
- `actionlint` locally: not installed. CI runs it in `make check`.

## Known risks
- Not yet exercised on GitHub. The first PR run should confirm one run per PR push and that a second quick push cancels the first.
- A branch with no PR gets no CI at all. A draft PR is enough; workflow_dispatch also still works for a one-off run.
- The repo is now public (O1). Fork PRs still use `pull_request` (read-only token, no secrets), same as before; no `pull_request_target` was added.
- Security specialist review is owed (`.github/workflows/**` trigger).

## Next step
Owner pushes the branch and opens a draft PR; its run is both Gate 1 (actionlint included) and the proof that the PR trigger works (push a second commit quickly to see the first run cancelled). Gate 2 review plus security review alongside. Apply the docs below at close-out and mark the task done in `.harness/status.yaml` and the workflow.md Phase 2 status table.

## Docs
Owed at close-out (outside paths_allowed, not edited here):
- CLAUDE.md, Commands: the heavy-test line, "awaiting CI" now needs a PR (a draft is enough).
- workflow.md, Stage 0 step 4: same point, CI starts from the PR, not from a branch push.
- `.harness/handoffs/orchestrator.md`, How to run a task, steps 4 and 6: open a (draft) PR to get CI.
- PRD.md R7.3: "on every push" becomes "on every PR update and every push to main".
- docs/threat-model.md section 1 and the P1-5 rows: CSO-owned, the next CSO run closes P1-5.
- `.harness/status.yaml` and workflow.md `### Phase 2 status`: mark p2d-ci-triggers done.
- Heads-up, not made false by this diff: CLAUDE.md Status says "no CI runs until it resets", which is stale since the repo went public (O1).

## Evidence
- `LOOM_TASK=p2d-ci-triggers ../p2b-qa-tests-batch/.venv/Scripts/python.exe -m pytest -q tests/test_ci_triggers.py tests/test_ci_workflow.py`: 25 passed (p4-plan recorded 3 failed, 22 passed before the change).
- Same interpreter, `pytest -q -m "not heavy"`: 1222 passed, 62 skipped, 14 deselected.
- `python tests/docs_check.py`: passed.
- actionlint not run locally (not installed).
