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

## Review round 1 fix (implementer)

Status: partial, awaiting CI. The 16 shell tests skip on Windows, so they have not run.

- Both findings fixed in `.github/workflows/weekly_scripts.yml`:
  - validate and open-pr download the artifact to `${{ runner.temp }}/artifact`, never over the checkout.
  - Both run one text-identical step, "Copy the new scripts from the artifact", before pytest and before any git command, with no token in its env. It runs under `LC_ALL=C`, walks `$RUNNER_TEMP/artifact/queue/approved` with `find -print0`, and fails on a symlink, directory, FIFO or other non-regular file, on a name not matching `^[a-z0-9]+(-[a-z0-9]+)*\.json$`, on an existing file that differs (`cmp -s`), and when nothing new was copied. Byte-identical existing files are skipped.
  - open-pr then runs `git add -- queue/approved` (only new files are untracked-or-changed) and `gh pr create --body-file "$RUNNER_TEMP/artifact/out/batch/pr_body.md"`. The old `git diff --quiet` and `git ls-files --exclude-standard` guards are gone.
  - validate: `cache: pip` removed, explicit `permissions: contents: read`, job comment corrected.
- Decision: hooks are disabled with `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=core.hooksPath`, `GIT_CONFIG_VALUE_0=/dev/null` in the commit step env instead of `git -c ...` on each call. It is the same effect for every git call, `gh`'s included, and the locked `test_weekly_workflow.py` needs the literal `git push` in the step. Needs git 2.31 or later (ubuntu-latest has it).
- Gate 2 notes: every guard has an explicit failure `echo`; `LC_ALL=C` is set. The earlier `--no-deps` wording was wrong: the hash proof ran `pip download --require-hashes -r requirements-generate.txt` without `--no-deps` (see Evidence).
- Not changed: pytest in validate is still an unhashed pin (optional per the task).
- Docs: unchanged from the list above; architecture.md section 4 should also say the artifact is extracted to the runner temp folder and filtered by the shared copy step.
- Evidence: `LOOM_TASK=p2-weekly-hardening pytest -q tests/test_weekly_hardening.py tests/test_weekly_workflow.py tests/test_workflow_safety.py`: 48 passed, 16 skipped (shell tests, Windows). actionlint and the shell tests await CI.

## Review round 1

Gate 2 approved. The security review blocked on two findings in `.github/workflows/weekly_scripts.yml`. The Architect updated `tests/test_weekly_hardening.py` (this task's own test file; `tests/test_weekly_workflow.py` is unchanged, since no done test asserts `path: .`) and the P2-2 and P2-4 notes in the task YAML. The implementer fixes the workflow next.

### Blocking findings
1. HIGH, open-pr. The artifact is extracted with `path: .` over a checkout that keeps credentials (`persist-credentials: true`, `GH_TOKEN` in env). A compromised generate job can ship `.git/hooks/*`, `.git/config` (`core.fsmonitor`) or any file outside queue/approved, which then runs on `git diff`, `git switch` or `git commit` with the write token.
2. MEDIUM, validate. The same `path: .` extraction runs before pytest, so a planted root `conftest.py`, `pytest.py`, `pyproject.toml` or an overwritten tests file makes validate pass vacuously.

### Fix direction
- Both jobs download to `${{ runner.temp }}/artifact` (the test pins exactly that path).
- One copy step, text-identical in validate (before pytest) and open-pr (before any git command, no `GH_TOKEN` in its env). It walks `$RUNNER_TEMP/artifact/queue/approved` with a NUL-safe loop under `LC_ALL=C` and fails on:
  - a symlink, directory, FIFO or other non-regular file;
  - a name not matching `^[a-z0-9]+(-[a-z0-9]+)*\.json$`, subfolders included.
- An entry already in the checkout is skipped when byte-identical (`cmp -s`) and fails the job when it differs. Generate uploads the whole folder, so the tracked `sample-65s.json` comes back unchanged every run. A literal "refuse any existing file" would fail every run. This check replaces `git diff --quiet`.
- Copy only new files into `queue/approved/`. Fail with a message when there are none.
- In open-pr, every git call uses `git -c core.hooksPath=/dev/null`. `gh pr create --body-file` reads `$RUNNER_TEMP/artifact/out/batch/pr_body.md`.
- validate: drop `cache: pip`, so a poisoned generate cache cannot seed the unhashed pytest install. Hash-pinning pytest is optional. Add an explicit job-level `permissions: contents: read`, and fix the job comment: the job still has a read-only `GITHUB_TOKEN`, so "no token" is wrong.
- The shell harness gives `RUNNER_TEMP` in env and resolves `${{ runner.temp }}` in step `env:` to it. Any other expression in step env becomes `dummy`.

### Gate 2 notes (non-blocking)
- What changed says `--no-deps`, but Evidence ran without it. State which one ran.
- Give every guard an explicit failure `echo`. This includes the old `git diff` guard if any form of it stays.
- `git ls-files --exclude-standard` drops ignored files silently. Remove it or justify it in the handoff.
- Set `LC_ALL=C` for the bash regex, so `[a-z]` cannot match non-ASCII letters in other locales (the test now includes `café.json`).

### Test changes
- New static tests:
  - `test_artifact_never_lands_on_the_checkout[validate|open-pr]`
  - `test_validate_job_is_explicitly_read_only_and_uncached`
  - `test_validate_copies_the_artifact_with_the_open_pr_step`
  - All three are added to `test_acceptance`.
- New shell tests:
  - `test_open_pr_refuses_a_non_regular_file[symlink|directory|fifo]`
  - `test_open_pr_ignores_files_outside_queue_approved` (planted `.git/hooks`, `.git/config`, `conftest.py`, `pytest.py`, `pyproject.toml`, tests file)
  - `test_open_pr_runs_no_git_hooks` (hooks planted in the checkout must not run)
- Changed shell tests:
  - The artifact fixture now lives in `<tmp>/runner/artifact` and the checkout stays clean.
  - The success test also checks `--body-file` under the temp folder and that no `out/` reaches the checkout.
  - The bad-name list gains `café.json` and `.hidden.json`.
- `test_open_pr_refuses_a_changed_approved_script[delete]` is dropped, and the edit case is renamed `test_open_pr_refuses_an_edited_approved_script`. A file missing from a temp-folder artifact deletes nothing, so there is no deletion to refuse.
- Against the current workflow, 5 static tests fail on Windows: the two path tests, permissions/cache, the shared copy step and acceptance. The shell tests skip locally, so CI proves them.
