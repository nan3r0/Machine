# Handoff: p1-docs-check

## Goal
A free, model-free CI check (`tests/docs_check.py`) that fails when the docs drift from each other or from the repo.

## Status
done (local Gate 1 green; CI not yet run, branch not pushed)

## What changed
- `tests/docs_check.py` (new, locked by `tests/**`): `problems(root)` returns one line per problem; `main` prints them plus a summary line and exits 1 if any. Checks, in output order: status.yaml `done` vs task YAMLs and the workflow.md Phase 1 status table (both directions); backticked `tests/...` refs in the workflow.md criterion-to-test map (file exists, `path::name` names a function found by `ast.walk`, so class methods count); task ids in the CLAUDE.md `## Status` section have a task YAML; every done task has a handoff with a non-empty `## Docs` section; every lessons.md entry under `## Entries` has a non-empty value for every field of the `## Entry format` template. Optional argument: repo root (used by the tests).
- `tests/test_docs_check.py` (new, locked): a clean temporary fixture repo with its own "no problems" test (and a CRLF variant), one negative test per rule asserting the exact message, a CLI test, wiring tests for Makefile and ci.yml, a lock test, and `test_acceptance` running the script on the real repo.
- `Makefile`: `python tests/docs_check.py` is the first line of `make check` (fastest step, fails first).
- `.github/workflows/ci.yml`: new `Docs check` step right after the scope check, before the installs, so drift fails in seconds. PyYAML is already installed by the scope check step on every branch.

## Decisions made (and why)
- `.harness/locks.yaml` unchanged: `tests/**` already locks both new files. `test_docs_check_and_its_test_are_locked` asserts it instead.
- CI runs the branch copy of the script, not the base ref's copy like the scope check. The base has no copy yet, the check is not a security control, and the scope check already blocks implementer edits under `tests/`.
- The check runs twice in CI (own step and inside `make check`), as the task asked. The own step gives a fast failure; `make check` keeps it in the local Gate 1 run.
- Lessons fields are read from the `## Entry format` template (text before the first `:`), so changing the template changes the check. An empty value counts as a missing field.
- Status table rows count only when the first cell (backticks stripped) is a whole task id and the status cell starts with `done`, so "Harness setup (...)" and range rows like "p1-tts-kokoro to p1-phase-review" are ignored.
- Task ids in the CLAUDE.md Status section are matched as `p<N>-...` or `h-...`, the two prefixes in use.
- No sections found (heading missing) for the status table, criterion map, CLAUDE.md Status or lessons sections means no problems from that rule, not an error. Missing `workflow.md`, `CLAUDE.md`, `lessons.md` or `status.yaml` raise (traceback, exit 1).

## Tried and abandoned
- Running the tests with the system Python: it has a stray `tests` package in site-packages that shadows the repo's `tests` package (`cannot import name 'docs_check' from 'tests'`), and `test_scope_check.py` fails the same way. Used `.venv/Scripts/python` instead; no repo change needed.

## Known risks / fragile spots
- Bare test names in the criterion map (the parenthesised names in the R2.1 row, `check_wav`) are not checked; only backticked `tests/...` refs are.
- Headings are matched exactly (`### Phase 1 status`, `### Criterion to test map`, `## Status`, `## Entries`, `## Entry format`, `## Docs`). Renaming one silently disables that rule. A Phase 2 status table needs the heading added to `workflow_done`.
- Task ids with a prefix other than `p<N>-` or `h-` in the CLAUDE.md Status section are not seen.
- Once `p1-docs-check` is in status.yaml `done`, `test_acceptance` runs on main: from then on any doc drift fails the main suite, not only the CI step.

## Next step for whoever picks this up
- Push `task/p1-docs-check` and get CI green, then Gate 2 (the reviewer; security reviewer too, since `ci.yml` matches `.github/workflows/**`).
- At close-out, add `p1-docs-check` to `.harness/status.yaml` `done` and the `| p1-docs-check | done, ... |` row to the workflow.md Phase 1 status table **in the same commit**, or main CI goes red on the new check. The same applies to every later task.

## Docs
- workflow.md: Phase 1 status table gets a `p1-docs-check` done row in the same commit that adds it to status.yaml (see Next step). Step 4 (Gate 1 locally) adds `python tests/docs_check.py`. Row R7.5 can name `tests/test_docs_check.py` next to the scope check.
- CLAUDE.md: Commands, Gate 1 line: add `python tests/docs_check.py` to the local commands and "docs check" to what `make check` adds. Status line: p1-docs-check done; next is the five implementer tasks.
- spec.md section 6 (Gate 1 list, line 70): add the docs check to what `make check` runs.
- PRD.md R7.5: optionally add the docs check to the list of tools `make check` runs.
- HARNESS.md section 10 Stage 0 close-out: state that status.yaml and the workflow.md status row must change in the same commit (the check fails otherwise).
- lessons.md, Traps: "Run tests with the project venv (`.venv/Scripts/python -m pytest`); the system Python has a `tests` package in site-packages that shadows the repo's `tests` imports." Not a mistake in this task, so no entry; owner's call whether it belongs in Traps.

## Evidence
- `LOOM_TASK=p1-docs-check .venv/Scripts/python -m pytest -q --tb=short tests/test_docs_check.py tests/test_ci_workflow.py tests/test_scope_check.py`: 77 passed.
- Before the script existed: collection failed (import error). Before the Makefile and ci.yml edits: only the wiring test failed, the other 20 passed.
- `LOOM_TASK=p1-docs-check .venv/Scripts/python -m pytest -q --tb=short`: 121 passed, 110 skipped (heavy and unbuilt tasks).
- `.venv/Scripts/python -m pytest -q .harness/tests`: 69 passed.
- `.venv/Scripts/ruff check .`: all checks passed. `.venv/Scripts/mypy --strict tests/docs_check.py`: no issues.
- `.venv/Scripts/python tests/docs_check.py` on this branch: `docs check passed`.
- Not run locally: actionlint on the edited ci.yml, the rest of `make check` (CI only).
