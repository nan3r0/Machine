# Handoff: p1-contracts

## Goal
Tooling, contracts, fixtures and locked tests for Phase 1, so the five implementer tasks can start against fixed interfaces.

## Status
done (local gates green; heavy tests and the CI workflow itself are unverified until the first CI run)

## What changed
- `pyproject.toml`: ruff (E, F, I, B; line length 110), mypy strict with the pydantic plugin, pytest (`testpaths`, `pythonpath = ["."]`, `-p pytester`, `heavy` marker), mutmut paths. mypy `ignore_missing_imports` for every heavy import an implementer may need (`kokoro`, `misaki`, `stable_whisper`, `whisper`, `torch`, `torchaudio`) and for `soundfile`, which ships no type information.
- `requirements.txt`, `requirements-dev.txt`, `requirements-heavy.txt`: exact pins, recorded with reasons in spec.md section 7. semgrep and mutmut carry a `sys_platform != "win32"` marker so one dev file serves Windows and CI.
- `pipeline/constants.py`: every number from spec.md section 4, plus voice, safe-zone, file-size, caption and golden-frame values.
- `pipeline/schema.py`: strict Pydantic models (`extra="forbid"`, no type coercion, frozen). `Script.narration_text()` and `narration_words()` are the one tokenisation voice, align, captions and QA share. `WordTiming` rejects end before start; `QAReport` requires `passed` to match `failures`; `QAFailure.check` is a fixed set of names.
- Stubs with signatures and docstrings, bodies raising NotImplementedError: `voice/kokoro.py` (`synthesize`, `check_wav`, `VoiceError`), `voice/align.py` (`align_words`, `to_word_timings`, `AlignError`), `render/captions_ass.py` (`escape_ass_text`, `build_ass`), `render/compose.py` (`subtitles_filter_value`, `build_ffmpeg_args`, `compose`, `ComposeError`), `render/qa.py` (`VideoStats`, `duration_range_for`, `evaluate`, `measure`, `run_qa`), `render_one.py` (`render`, `main`, `DEFAULT_CACHE_DIR`). Each heavy step has a pure, locally testable part.
- `queue/approved/sample-40s.json`: the Racetrack Playa sliding rocks, 106 words. Every number and name is from the PLOS ONE paper's abstract (doi 10.1371/journal.pone.0105948): speculation since the 1940s, more than 60 rocks moved on December 20, 2013, ice 3 to 6 mm thick, up to 224 m of travel, a team including Scripps Institution of Oceanography scientists. No individuals are named.
- `tests/conftest.py`: task-aware selection; unknown `LOOM_TASK` is a usage error; heavy tests run only when `CI=true`.
- Tests: `test_schema.py`, `test_conftest_selection.py` (pytester), `voice/test_kokoro.py`, `voice/test_align.py`, `render/test_captions_ass.py`, `render/test_compose.py`, `render/test_qa.py`, `test_render_one.py` (fakes for wiring, heavy golden render), `test_workflows.py` (render.yml), `test_ci_workflow.py`, `test_scope_check.py`. Helpers: `wavs.py`, `media.py`, `workflow_rules.py`.
- `tests/scope_check.py`: the server-side twin of the lock hook. Reads the task YAML and `locks.yaml` from the base ref, diffs with `--no-renames`.
- `.github/workflows/ci.yml`: scope check, LOOM_TASK from the branch (through `env:`, regex-validated), ffmpeg and espeak-ng, all three requirement files, gitleaks and actionlint with sha256 checks, model cache, `make check`, `out/frames/` upload. A `workflow_dispatch`-only `reports` job runs coverage, mutmut, pip-licenses and pip-audit and uploads `out/reports/`.
- `Makefile` (`check`), `.github/dependabot.yml` (pip and actions, weekly), `.gitignore` additions, `.harness/locks.yaml` (`tests/**`, `pipeline/schema.py`, `pipeline/constants.py`, `.github/workflows/ci.yml`, `Makefile`).
- `spec.md` sections 4 and 7: final values and pins. `workflow.md`: criterion to test map with real names, status row.

## Decisions made (and why)
- Voice package is `kokoro` 0.9.4, as the owner asked ("stick with kokoro"). I read that as the PyTorch package rather than kokoro-onnx; my clarifying question went unanswered before resuming. kokoro leaves transformers, spaCy and the spaCy model loose, so they are pinned, and `en_core_web_sm` is installed from its release wheel so misaki never pip-installs at runtime. If the owner meant kokoro-onnx, swap the heavy pins and the mypy override names; the onnx weight URLs and sha256 are below.
- torch and torchaudio pinned to 2.11.0 CPU builds: torchaudio has no release past 2.11 and must match torch. stable-ts 2.19.1 calls only `torchaudio.save` (not on the align path) and `torchaudio.functional` filters.
- Heavy tests run when `CI=true`, not when a tool happens to be installed, matching the owner's "heavy tests never run locally".
- Steps are called through module attributes in `render_one`, documented in its docstring, so its tests replace them with fakes and the wiring is fully tested without heavy packages.
- `escape_ass_text` must write braces as `\{` and `\}` and must not leave `\N`, `\n` or `\h`; how it neutralises a backslash is left to the implementer.
- Caption End may run up to the next word's start, so the line can stay on screen between words.
- QA picks the format from word count (`duration_range_for`), so the schema needs no format field.
- `VideoStats` carries the voice duration so QA can check video against voice (R5.3) and timings against the audio.
- The golden render lives in `tests/test_render_one.py::test_acceptance`, since a heavy test owned by no task would fail CI until everything is built. Compose's heavy test also writes frames, so visual-qa has something to look at before render-cli exists.
- Locks cover `tests/**` rather than each file, so new helpers and fixtures are locked too.
- Ruff settings chosen so the existing `.harness/` code passes untouched (it is outside this task's scope).
- Action pins (lightweight tags, so the tag SHA is the commit): checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`, setup-python v7.1.0 `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`, upload-artifact v7.0.2 `cf430e030ddbb5b0abf93d22962f4752f3646cd9`, cache v6.1.0 `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`.
- kokoro-onnx fallback weights (GitHub release `thewh1teagle/kokoro-onnx` tag `model-files-v1.0`, streamed and hashed):
  - `kokoro-v1.0.onnx` (325532387 bytes): `7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5`
  - `voices-v1.0.bin` (28214398 bytes): `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`

## Tried and abandoned
- kokoro-onnx as the voice package: lighter, but the owner asked to stay with kokoro.
- torch 2.15.0: no matching torchaudio.
- numpy 2.5: needs Python 3.12; the owner's machine runs 3.11.
- Ruff with `UP` rules and line length 100: flagged existing `.harness/` files this task may not edit.
- Two QA alignment cases first broke word order as well as the fault they named, so a QA implementation could pass them for the wrong reason; rewritten to change one thing each.

## Known risks / fragile spots
- Not verified locally, for CI to confirm:
  - All heavy tests (Kokoro, stable-ts, FFmpeg render, QA on real video, golden render). Each is skipped locally by design.
  - The heavy install: the `+cpu` torch wheels from the extra index, kokoro 0.9.4 with transformers 5.22.1 (it imports `AlbertModel` and `AlbertConfig`), spaCy 3.8.18 with the 3.8.0 model, numba's numpy cap. Install time may be long on the first run until the pip cache warms.
  - `make check` itself: bandit, semgrep (`p/python`, ERROR only, scans `tests/` too, which call git and ffmpeg through argument lists), gitleaks on the full history, pip-audit (may skip the `+cpu` packages), actionlint on `ci.yml`.
  - The `reports` job (mutmut 3 config in pyproject).
- Contracts not proven implementable by a reference implementation, mainly `to_word_timings` under the hypothesis property (pieces with arbitrary, even inverted, times must still give clamped monotonic output) and the caption property (End bounds with overlapping timings). I believe both are satisfiable; an implementer who disagrees should write `CONTRACT_CHANGE.md`.
- `escape_ass_text` requires `\{` and `\}`. If libass on the runner renders the backslash visibly, the golden frames will show it and the contract needs a change.
- The compose heavy test's hand-written captions use DejaVu Sans, which `ubuntu-latest` is expected to have.
- On a push run of a stacked branch, the scope check diffs against `origin/main`, as instructed; the PR run (against `github.base_ref`) is the authoritative one.
- An automated security review of the commits flagged two issues, both addressed in the last commit: (1) CI ran the scope checker from the branch, so a branch could edit it. It now runs the copy from the base ref; only a base without one (this PR) falls back to the branch copy. `ci.yml` and `Makefile` are now locked too. Still open: a branch can edit `ci.yml` itself and drop the step. The hook blocks that locally and the scope check flags it on later task PRs, but nothing server side stops it on a free private repo without required workflows, so the owner's PR diff review remains the backstop. (2) `Task/x` skipped the check; the prefix is now matched case-insensitively (regression test `test_task_prefix_in_other_case_is_not_skipped`). Non-task branches are still skipped on purpose: the owner's own branches edit harness and admin files.
- Kokoro weights download from Hugging Face by repo id with no revision pin; an upstream change to `hexgrad/Kokoro-82M` would change the voice.

## Next step for whoever picks this up
- Push `task/p1-contracts`, open the PR and get CI green. Fix install or tool-config failures in this task's files; failures in a heavy test of an unbuilt task cannot happen, since those are skipped.
- Gate 2 plus the security specialist review (`ci.yml` matches `.github/workflows/**`).
- Outside this task's `paths_allowed`, for the owner: add `p1-contracts` to `.harness/status.yaml` after merge, update the CLAUDE.md Status line, and consider a lessons.md entry: "Writing to the main repo path instead of the worktree path was caught by the hook; always use the worktree root in absolute paths."
- Then the five implementer tasks can run in file-name order.

## Evidence
- `.venv/Scripts/python.exe -m ruff check .`: All checks passed.
- `.venv/Scripts/python.exe -m mypy --strict pipeline/`: Success, no issues found in 11 source files.
- `.venv/Scripts/python.exe -m pytest -q --tb=short --cov=pipeline` (LOOM_TASK=p1-contracts): 79 passed, 104 skipped, 0 failed; coverage 89% of the stubs.
- Each task's tests run against the stubs with `LOOM_TASK` set to that task: every non-heavy test fails with NotImplementedError (render.yml tests with FileNotFoundError), heavy tests skip, no collection errors. Counts: tts-kokoro 10 failed, 4 skipped; align 8 failed, 3 skipped; captions-ass 26 failed, 1 passed (`test_module_is_pure`, a guard); compose 6 failed, 1 passed (`test_no_shell_strings`, a guard), 3 skipped; qa 21 failed, 3 skipped; render-cli 11 failed, 1 skipped; actions-workflow 6 failed.
- `.venv/Scripts/python.exe tests/scope_check.py task/p1-contracts main`: scope check passed, 35 changed files.
- `.venv/Scripts/python.exe -m pytest -q --tb=short .harness/tests`: 51 passed.
- Local venv has only requirements.txt and requirements-dev.txt; no heavy packages installed.
