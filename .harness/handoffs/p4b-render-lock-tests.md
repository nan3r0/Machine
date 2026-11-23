# Handoff: p4b-render-lock-tests (test_author)

## Goal
Locked tests for CSO P1-4 heavy half (phase review T6): hash-checked installs in Workflow B's render job and in render.yml, from two lock files that p4b-render-lock creates.

## Status
done

## What changed (and why)
- New `tests/test_render_lock.py` (owned by p4b-render-lock, so it skips on main until that task is done):
  - `requirements-render-torch.txt` holds exactly torch and torchaudio at the versions in requirements-heavy.txt (torch keeps `+cpu`), each with `--hash=sha256:` and 64 hex characters.
  - `requirements-render.txt`: every line is `name==version` (extras allowed, as in `misaki[en]`) or a direct URL with `#sha256=`, and carries at least one `--hash=sha256`. Every pin of requirements.txt and requirements-heavy.txt other than torch and torchaudio appears at the same version, and the en_core_web_sm URL must equal the one in requirements-heavy.txt. Torch and torchaudio must not appear. Versions are read from the source files at test time, so a Dependabot bump fails until the lock is regenerated. Option lines (`--index-url`, `--extra-index-url`, `--find-links` and the like) are not requirements, so the strict line parser rejects them. Comment text is ignored, so the regenerate commands can sit in each file's header.
  - Both render paths: exactly two `pip install` lines. First: `--no-deps --require-hashes --index-url https://download.pytorch.org/whl/cpu -r requirements-render-torch.txt`, with no other index option. Second: `--require-hashes -r requirements-render.txt`, with no index option at all. So no `-r requirements-heavy.txt` or `-r requirements.txt` install is left. Option order is free; `--opt=value` forms are caught for the forbidden index options.
  - `test_acceptance` runs all four.
- `tests/workflow_rules.py`: `assert_torch_from_cpu_index_first` loosened to hold for the current install and the locked one. It now finds the torch install as a `pip install` line with `--no-deps` and the CPU `--index-url` (flag order free, so `--require-hashes` may sit between), and the heavy install as the first line with `-r requirements-heavy.txt` or `-r requirements-render.txt`. Torch must come first, and the heavy line must have no `--index-url` (PyPI only; that was the docstring's intent, now checked). `TORCH_INDEX_INSTALL` became `TORCH_INDEX` plus `HEAVY_INSTALLS`; nothing else used the old name. ci.yml still passes unchanged.
- `tests/test_workflows.py::test_installs_ffmpeg_and_heavy_requirements`: accepts either `-r requirements.txt` with `-r requirements-heavy.txt`, or `-r requirements-render.txt`.
- `tests/test_daily_publish_workflow.py`: no change needed; its `test_render_job` calls the loosened rule.

## Decisions made
- The lock parser is local to the new file, not shared with `tests/test_weekly_hardening.py`'s `pins`: that one cuts lines at any `#` (it would cut the en_core_web_sm URL) and has no extras.
- Only `#` at line start or after whitespace is a comment, as pip reads it.
- Extra pins in requirements-render.txt are allowed (transitive packages, and any build dependencies whisper's sdist needs).
- `--no-build-isolation` on the second install is allowed (the tests do not forbid extra flags), but a third `pip install` is not, per the task notes.

## Tried and abandoned
none

## Known risks
- p4b-render-lock's note allows pinning whisper's build dependencies "and install with --no-build-isolation after them". If that needs a separate pip install before the render lock, these tests refuse it (task notes: "no other pip install in those jobs"). The implementer would then write CONTRACT_CHANGE.md. Putting the build dependencies in requirements-render.txt with `--no-build-isolation` on the one install may not order them before the build, so the Linux proof (render.yml dispatch) decides.
- The positive path (well-formed lock files passing) is traced by hand only: I cannot create the lock files here (outside paths_allowed).

## Next step
Orchestrator merges this `docs/*` branch, then runs p4b-render-lock.

## Docs
- Applied: none.
- Owed (p4b-docs): workflow.md `### Phase 4 status` row for p4b-render-lock-tests; workflow.md criterion map gains `tests/test_render_lock.py` for P1-4 heavy half. lessons.md: no new mistake.

## Evidence
- `pytest -q --tb=short tests/test_workflows.py tests/test_daily_publish_workflow.py tests/test_ci_workflow.py tests/test_render_lock.py`: 34 passed, 5 skipped (the 5 are test_render_lock.py, owned by p4b-render-lock).
- `pytest -q --tb=line --noconftest tests/test_render_lock.py`: 5 failed, as intended on today's tree: both lock files missing, and both workflows still install from `$RUNNER_TEMP/torch.txt`. The heavy and light source files parse cleanly (the torch test got past them).
- `ruff check .`: passed. `mypy --strict pipeline/`: passed.
