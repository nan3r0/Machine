# Handoff: p2-entry-ci

## Goal
Workflow safety rules for every file in `.github/workflows/` with per-job allowlists (CSO P1-6), and a docs check that reads every `### Phase <n> status` table (phase review N9), plus the task-id false positive fix.

## Status
done (Test Author, locked files only). Branch `docs/p2-entry-ci-tests`, committed, not pushed.

## What changed (and why)
- `tests/workflow_rules.py`: new `safety_problems(workflow, name)`, `directory_problems(directory)` and `workflow_files(directory)`; `load` takes an optional `directory`. Allowlists `WRITE_JOBS` and `SECRET_JOBS`, keyed by (file, job id), seeded with exactly the two Phase 2 entries from the task. Rules: workflow-level permissions exactly `contents: read`; job permissions absent, `contents: read` or exactly equal to the allowlist entry; no `pull_request_target`; step and job-level (reusable workflow) `uses:` pinned to a full SHA; no `${{` in `run:`; any `secrets` reference (any case, any syntax incl. `toJSON(secrets)`, `secrets['X']`, `secrets: inherit`, bare `if:`) only as an allowlisted `secrets.NAME` in its job, never at workflow level and never inside `run:`; `github.token` only in an allowlisted write job; every checkout sets `persist-credentials: false` (the boolean) except in an allowlisted write job. `assert_safe(workflow, name="")` now wraps `safety_problems`, so ci.yml and render.yml keep their old checks plus the new ones; their tests are unedited.
- `tests/test_workflow_safety.py` (new): a clean `weekly_scripts.yml` fixture in tmp_path that uses every exception and passes on its own, 25 bad-workflow mutations, per-file allowlist, `.yaml` extension, empty directory, `assert_safe` raising, secret and write jobs disjoint, and `test_acceptance` over the real directory by glob (no parametrize over the glob, so an empty glob cannot pass as skipped).
- `tests/docs_check.py`: reads every `### Phase <n> status` table for the status.yaml cross-check; requires `### Phase 2 status`; a status row that names a task id anywhere must start with one; `TASK_ID_IN_TEXT` no longer matches after a letter, digit or hyphen (fixes `p2-plan` in `architect-p2-plan`).
- `tests/test_docs_check.py`: fixture gains a Phase 2 table and the `architect-p2-plan` mention; new tests for later-phase tables, the row rule, and the regex regression; messages updated with the same meaning.
- `workflow.md`: the "QA lead, CSO, Auditor" and "Phase review" rows split into `p1-qa-lead`, `p1-cso`, `p1-audit`, `p1-phase-review` rows.

## Decisions made
- Read-only review tasks (`p1-qa-lead`, `p1-cso`, `p1-audit`, `p1-phase-review`) are not in status.yaml, so their rows say "reviewed ..." rather than "done ...", which the cross-check would otherwise require in status.yaml. No exemption rule was added to the check.
- Secrets and `github.token` are matched in every key and string of the parsed tree, not only inside `${{ }}`, so bare `if:` expressions and `secrets: inherit` are caught. Fail closed: the word "secrets" in a step name would also fail; ci.yml and render.yml have none.
- `.harness/locks.yaml` unchanged: `tests/**` already locks both new and changed test files.

## Tried and abandoned
- A Python heredoc rewrite of `workflow_rules.py` mangled backslashes (`\b` became a backspace); repaired with the Edit tool. No effect on the result.

## Known risks
- `tests/test_workflow_safety.py` is owned by this task, so it runs only with `LOOM_TASK=p2-entry-ci` or once status.yaml lists p2-entry-ci. On a `docs/` branch CI sets no LOOM_TASK, so the acceptance test does not run on that PR; after merge it is dormant on main until close-out adds the id.
- p2-qa-lead, p2-cso, p2-audit and p2-phase-review hit the same "done means status.yaml" rule at their close-out. Either write "reviewed" or add them to status.yaml; an owner or Architect call.
- mypy is not run on `tests/`; `load` has a pre-existing `pop(True)` typing complaint under `mypy --strict tests/`.
- actionlint, bandit, semgrep not run locally (CI only).

## Next step
Orchestrator pushes, preferably as `task/p2-entry-ci` so CI sets LOOM_TASK, runs the scope check and the acceptance test; or merges as a docs/contracts PR and adds p2-entry-ci to status.yaml right after. Then p2-contracts can start (after owner decisions D2 to D6). Its `tests/test_weekly_workflow.py` must call `rules.assert_safe(wf, "weekly_scripts.yml")` (or rely on `directory_problems()`); without the name no allowlist applies and the write job and the secret fail.

## Docs
- `workflow.md`: Phase 1 rows rewritten (done here). Phase 2 status row for p2-entry-ci to "done" at close-out.
- `.harness/status.yaml`: add p2-entry-ci at close-out.
- `docs/threat-model.md` section 4.3 and section 8 table: P1-6 closed by p2-entry-ci (CSO-owned file; apply at close-out or in p2-cso).
- `.harness/handoffs/p1-phase-review.md` N9: fixed by p2-entry-ci (note only).
- `lessons.md` entry (close-out, outside paths_allowed): "Python heredoc rewrite mangled regex backslashes". What happened: a Bash heredoc feeding a Python rewrite of `tests/workflow_rules.py` turned `\b` into a backspace and `\n` into a real newline; a sed repair then dropped the backslash again. Root cause: two layers of escaping (shell, Python string) between the intended text and the file. Fix: repaired with the Edit tool. Rule going forward: edit source files with Edit or Write only, never through a shell or Python rewrite. Test added: none, process rule (ruff and pytest caught it at once).

## Evidence
- Red first: the new test file failed 32 of 32 before the helpers existed; docs check tests failed 25 of 34 before the fix (incl. the regex regression test).
- A bare `permissions:` (null) on a job first passed; the null-permissions case failed, then the rule was fixed to compare against `contents: read` for non-allowlisted jobs.
- Each rule shown failing by mutation (rule disabled in-process, test file run): workflow perms 3 fail, pull_request_target 1, job perms 6, pin 2, job-level uses 1, `${{` in run 1, secret in run 1, checkout 5, secrets 10, token 4, workflow-level scan 2, `.yaml` glob 1, empty dir 1, case-insensitive match 1.
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues (14 files).
- `pytest -q`: 332 passed, 108 skipped. `LOOM_TASK=p2-entry-ci pytest -q`: 365 passed, 75 skipped.
- `python tests/docs_check.py`: docs check passed. `pytest .harness/tests`: 69 passed.
