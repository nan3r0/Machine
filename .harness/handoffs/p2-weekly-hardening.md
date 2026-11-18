# p2-weekly-hardening

## Goal
CSO P2-1, P2-2, P2-4 and P2-6 on Workflow A: hashed install in the key job, new-scripts-only PR, a keyless validate job, no overlapping runs.

## Status
partial, awaiting CI. The 10 open-pr shell tests skip on Windows, so they have not run. Branch `task/p2-weekly-hardening`, committed, not pushed.

## What changed (and why)
- `requirements-generate.txt` (new): every direct pin from requirements.txt plus the six transitive packages, each with a sha256 line. Built from `pip download` with the three manylinux tags, hashed, then checked with `pip download --require-hashes --no-deps` into an empty folder (passed).
- `.github/workflows/weekly_scripts.yml`:
  - generate installs only with `--require-hashes -r requirements-generate.txt`; setup-python caches on that file (P2-1).
  - open-pr runs `git diff --quiet -- queue/approved`, so an edited or deleted tracked script fails the job. It then reads untracked files with `git ls-files --others -z`, fails on any name not matching `^[a-z0-9]+(-[a-z0-9]+)*\.json$` (subfolders included) or on an empty list, and stages only those (P2-2).
  - new `validate` job: needs generate, read-only default token, no secret, checkout without credentials, artifact download, hashed install plus `pytest==9.2.0` in a second call, runs `tests/test_queue_scripts.py`. open-pr needs `[generate, validate]` (P2-4).
  - workflow-level `concurrency: {group: weekly-scripts, cancel-in-progress: false}` (P2-6).
- `pyproject.toml`: mutmut `also_copy` gains `.gitignore` and `requirements-generate.txt`.

## Decisions made
- One wheel hash per package. With the three platform tags together pip picks a single wheel each, and no single tag resolves alone (numpy, pydantic-core, pyyaml). If the runner picks a different wheel, the generate job fails closed on the hash.
- Failing on an empty new-script list in open-pr, because an empty commit would fail anyway, now with a clear message.

## Tried and abandoned
- Downloading each platform tag on its own to collect extra wheel hashes: each one fails to resolve, as the task YAML warned.

## Known risks
- The first live run (owner manual acceptance) is the real proof that the runner's wheels match the hashes.
- Dependabot bumps of requirements.txt need a regenerated hash file; the pin test fails until then.
- `pyproject.toml` is also edited by `fix/mutmut-copy-sources` (already merged on main per git log); no conflict seen on this branch.
- actionlint is not installed locally; CI runs it.

## Next step
Push and let CI run: it must be green, including the 10 shell tests, before this task is done. Then Gate 2 and the security review. After merge the owner re-enables weekly-scripts and dispatches it once.

## Docs
- architecture.md section 4 (three jobs, hashed install) and section 7 (P2-2 and P2-4 closed).
- spec.md section 7: list `requirements-generate.txt`.
- docs/threat-model.md: P1-4 light half and the P2-n rows (CSO at phase end).
- lessons.md: none.

## Evidence
- `LOOM_TASK=p2-weekly-hardening pytest -q tests/test_weekly_hardening.py tests/test_weekly_workflow.py tests/test_workflow_safety.py`: 44 passed, 10 skipped (shell tests, Windows).
- Full `pytest -q --tb=short`: 729 passed, 179 skipped.
- `ruff check .`: passed. `python tests/docs_check.py`: passed.
- `pip download --require-hashes -r requirements-generate.txt` with the three platform flags: succeeded.
- Not run: mypy (no pipeline code changed), actionlint (not installed locally).
- Venv: `../p2-weekly-workflow/.venv`.
