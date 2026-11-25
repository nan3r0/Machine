# p4c-ci-lock-resolve

## Goal
Add a `lock-resolve` job to ci.yml that resolves every hashed lock on each push and PR, so a Dependabot bump pip cannot resolve goes red in CI instead of in a live workflow.

## Status
partial: awaiting CI run on the PR (the first run is the proof).

## What changed (and why)
- .github/workflows/ci.yml: new job `lock-resolve` between `check` and `reports`. Checkout and setup-python use the same SHAs as the check job (persist-credentials false, Python 3.12, cache: pip). Step 1 makes a fresh venv, installs requirements-render-torch.txt for real (`--no-deps --require-hashes` from the PyTorch CPU index), then runs `pip install --dry-run --require-hashes -r requirements-render.txt`. Step 2 makes another fresh venv and dry-runs requirements-generate.txt. No `if`, `needs`, secrets, `permissions`, `continue-on-error` or `${{ }}` in run. timeout-minutes 20.

## Decisions made
- Shape exactly as the task notes say; the backlog's `--platform` command is not used (reasons in the task YAML).
- cache: pip with the same dependency path as the check job, so the torch wheel usually comes from the shared pip cache. Hash checking still applies to cached files.
- timeout-minutes 20: the torch CPU wheel is about 200 MB and the two sdists build metadata in isolation; a few minutes is expected.

## Tried and abandoned
none

## Known risks
- Runtime: first run downloads torch plus every render wheel (dry-run still downloads to check hashes). If it nears 20 minutes, raise the timeout rather than drop the render locks.
- Both jobs save the pip cache under the same key; whichever saves first wins. Harmless, just a cache miss sometimes.
- Only checked against pip 23.0.1 help locally; the venv pip on the runner comes from Python 3.12's ensurepip, which supports `--dry-run`.
- actionlint is not installed locally; the check job's `make check` runs it on the PR.
- The job is not a required check until the owner adds it to the main ruleset (owner decision in the task notes), so a red run does not yet block a merge.

## Next step
Push, open the PR, read the lock-resolve run. Then the owner makes `lock-resolve` a required status check on main with "require branches to be up to date".

## Docs
- workflow.md status row for p4c-ci-lock-resolve at close-out.
- docs/runbook.md: a red `lock-resolve` on a Dependabot PR means the bump cannot resolve; close it or group it with what pins it (close-out, scribe).
- .harness/status.yaml: mark done after a green CI run.
- docs/threat-model.md:90 (P4b-1 residual c, a Linux-only dependency missing from a hand-made lock): once CI is green, note that `lock-resolve` now resolves the render and generate locks on Linux on every push and PR (CSO, at the next threat-model update).
- spec.md section on gates (near line 146, install order): add one line that CI's `lock-resolve` job resolves every hashed lock with `--require-hashes` in fresh venvs, outside `make check`.

## Evidence
`LOOM_TASK=p4c-ci-lock-resolve pytest tests/test_ci_lock_resolve.py tests/test_ci_workflow.py tests/test_ci_triggers.py -q --tb=short` (temporary empty tests/__init__.py, removed): 42 passed. `ruff check .` clean. `python tests/docs_check.py` passed. actionlint not available locally. Re-run on the committed tree: docs_check passed, `pytest .harness/tests -q`: 90 passed.
