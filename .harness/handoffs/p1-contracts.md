# Handoff: p1-contracts

## Goal
Tooling, contracts, fixtures and locked tests for Phase 1, so the five implementer tasks can start against fixed interfaces.

## Status
partial (paused by the owner after the Kokoro checksum step; no contracts or tests written yet)

## What changed
- `pyproject.toml`: ruff (E, F, I, B; line length 110), mypy strict with the pydantic plugin, pytest config with `testpaths = ["tests"]`, `-p pytester` and the `heavy` marker. mypy `ignore_missing_imports` overrides for every heavy import name an implementer may need (`kokoro_onnx`, `onnxruntime`, `stable_whisper`, `whisper`, `torch`, `torchaudio`) plus `soundfile`, which ships no type information.
- `requirements.txt`: light runtime pins (pydantic 2.14.2, pyyaml 6.0.3, soundfile 0.14.0, numpy 2.4.6).
- `requirements-dev.txt`: pytest 9.2.0, pytest-cov 7.1.0, hypothesis 6.170.14, ruff 0.17.3, mypy 2.4.1, types-PyYAML 6.0.12.20261030, bandit 1.9.4, pip-audit 2.10.1, pip-licenses 5.5.5, and semgrep 1.183.0 and mutmut 3.8.1 behind a `sys_platform != "win32"` marker, so one dev file serves both Windows and CI and Dependabot still tracks every pin.
- `requirements-heavy.txt`: torch 2.11.0+cpu and torchaudio 2.11.0+cpu from the PyTorch CPU index, stable-ts 2.19.1, openai-whisper 20250625, kokoro-onnx 0.6.1.
- `.gitignore`: added `.venv/`, tool caches, `.coverage`, `.hypothesis/`, `.harness/PAUSE`, `.harness/loom.lock`, `.harness/limit_state.json`.
- Every pin was checked on PyPI and is the newest stable release published on or before 2026-11-01 (at least two weeks old).

## Decisions made (and why)
- kokoro-onnx instead of kokoro: kokoro 0.9.4 pulls transformers, spaCy and misaki (with a runtime spaCy model download) and has not been released since 2025-04. kokoro-onnx runs on onnxruntime, bundles espeak through espeakng-loader and was released 2026-08. torch is still installed for stable-ts. Weights come from the GitHub release `thewh1teagle/kokoro-onnx` tag `model-files-v1.0` (`kokoro-v1.0.onnx`, 325532387 bytes; `voices-v1.0.bin`, 28214398 bytes). The release publishes no digests, so the sha256 values were computed by streaming the files; see Evidence. Plan: put URLs, sizes and sha256 in `pipeline/constants.py` so an implementer cannot swap the model.
- torch pinned to 2.11 rather than 2.15: torchaudio's last release line is 2.11, and the two must share a minor version. stable-ts 2.19.1 uses only `torchaudio.save` (output paths not used by `align()`) and `torchaudio.functional` filters, so 2.11 is expected to work.
- numpy 2.4.6, not 2.5: numpy 2.5 needs Python 3.12 and the owner's machine runs 3.11. numba (via openai-whisper) caps numpy below 2.6, so this fits.
- Ruff rule set and line length chosen so the existing `.harness/` code passes without edits (it is outside this task's scope). `.claude/` is excluded because the hook is admin-only.
- Action pins (commit SHAs, all lightweight tags): actions/checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`, actions/setup-python v7.1.0 `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`, actions/upload-artifact v7.0.2 `cf430e030ddbb5b0abf93d22962f4752f3646cd9`.
- CI binaries: gitleaks 8.30.1 (`gitleaks_8.30.1_linux_x64.tar.gz`, sha256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`), actionlint 1.7.12 (`actionlint_1.7.12_linux_amd64.tar.gz`, sha256 `8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8`).
- Sample script topic: the Racetrack Playa sliding rocks of Death Valley, solved in PLOS ONE 9(8): e105948, published 2014-08-27 (doi 10.1371/journal.pone.0105948). Verified from the paper's abstract: speculation since the 1940s; more than 60 rocks moved on December 20, 2013; GPS-instrumented rocks moved up to 224 m between December 2013 and January 2014; ice 3 to 6 mm thick; winds about 4 to 5 m/s; rock speeds 2 to 5 m/min; lead author affiliation Scripps Institution of Oceanography. Plan: name only the organisation, not the authors.

## Tried and abandoned
- `kokoro` (PyTorch package): heavier dependency chain and stale; see Decisions.
- torch 2.15.0: no matching torchaudio release.
- Ruff with `UP` rules and line length 100: flagged existing `.harness/` files this task may not edit.

## Known risks / fragile spots
- The heavy install (torch CPU wheels with a `+cpu` local version, onnxruntime, numba) has not been tried; CI will be the first install. pip-audit may skip the `+cpu` packages.
- torchaudio 2.11 with stable-ts 2.19.1 is reasoned from source, not run.

## Next step for whoever picks this up
Remaining items from `00_contracts.yaml` notes, in this order:
1. `pipeline/constants.py` (numbers from spec.md section 4, safe zone, file-size range, voice defaults, Kokoro URLs, sizes and sha256) and `pipeline/schema.py` (strict Pydantic, `extra="forbid"`, narration text and word helper).
2. Stubs raising NotImplementedError: `voice/kokoro.py`, `voice/align.py`, `render/captions_ass.py`, `render/compose.py`, `render/qa.py`, `render_one.py` (steps called through module attributes so tests can monkeypatch them), plus empty `__init__.py` files.
3. `queue/approved/sample-40s.json` from the verified facts above, about 105 words counted with the schema helper.
4. `tests/conftest.py` (task-aware selection, fail loudly on unknown `LOOM_TASK`, heavy tests run only when `CI=true`), per-task tests with `test_acceptance` names matching the task YAMLs, hypothesis caption properties with `deadline=None`, golden render inside `tests/test_render_one.py`, pytester tests for the conftest, `tests/scope_check.py` plus its tests (`git diff --name-only --no-renames`, task and locks read from the base ref).
5. Run each task's tests against the stubs with `LOOM_TASK` set to that task: non-heavy tests must fail with NotImplementedError, none may error at collection.
6. `.harness/locks.yaml`, `Makefile`, `.github/workflows/ci.yml` (branch name through `env:`, validated by regex; scope check base `github.base_ref` or `origin/main`), `.github/dependabot.yml`, spec.md pins and kokoro-onnx note, workflow.md test map.
7. Outside this task's `paths_allowed` (owner to do): a lessons.md entry if any mistake is found, and the CLAUDE.md Status line.

## Evidence
- `ruff check .`: all checks passed (with the current pyproject, on the existing repo files).
- mypy and pytest not run yet: there is no `pipeline/` or test code.
- Local venv: `.venv` with requirements.txt and requirements-dev.txt installed; no heavy packages.
- Kokoro sha256, computed by streaming each file from the release URL (not saved to disk):
  - `kokoro-v1.0.onnx`: `7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5`
  - `voices-v1.0.bin`: `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`
