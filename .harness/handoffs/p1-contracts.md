# Handoff: p1-contracts

## Goal
Tooling, contracts, fixtures and locked tests for Phase 1, so the five implementer tasks can start against fixed interfaces.

## Status
done after review round 2 (`.harness/reviews/p1-contracts-round2.md`): every item fixed, local gates green. Heavy tests and the CI install are still unverified until the next CI run.

## What changed
- `pyproject.toml`: ruff (E, F, I, B; line length 110), mypy strict with the pydantic plugin, pytest (`testpaths`, `pythonpath = ["."]`, `-p pytester`, `heavy` marker), mutmut paths. mypy `ignore_missing_imports` for every heavy import an implementer may need (`kokoro`, `misaki`, `stable_whisper`, `whisper`, `torch`, `torchaudio`) and for `soundfile`, which ships no type information.
- `requirements.txt`, `requirements-dev.txt`, `requirements-heavy.txt`: exact pins, recorded with reasons in spec.md section 7. semgrep and mutmut carry a `sys_platform != "win32"` marker so one dev file serves Windows and CI.
- `pipeline/constants.py`: every number from spec.md section 4, plus voice, safe-zone, file-size, caption and golden-frame values.
- `pipeline/schema.py`: strict Pydantic models (`extra="forbid"`, no type coercion, frozen). `Script.narration_text()` and `narration_words()` are the one tokenisation voice, align, captions and QA share. `WordTiming` rejects end before start; `QAReport` requires `passed` to match `failures`; `QAFailure.check` is a fixed set of names.
- Stubs with signatures and docstrings, bodies raising NotImplementedError: `voice/kokoro.py` (`synthesize`, `check_wav`, `VoiceError`), `voice/align.py` (`align_words`, `to_word_timings`, `AlignError`), `render/captions_ass.py` (`escape_ass_text`, `build_ass`), `render/compose.py` (`subtitles_filter_value`, `build_ffmpeg_args`, `compose`, `ComposeError`), `render/qa.py` (`VideoStats`, `duration_range_for`, `evaluate`, `measure`, `run_qa`), `render_one.py` (`render`, `main`, `DEFAULT_CACHE_DIR`). Each heavy step has a pure, locally testable part.
- `queue/approved/sample-40s.json`: the Racetrack Playa sliding rocks, 98 written words after review round 2 (first trimmed from 106: Kokoro speaks numbers in full and pauses at sentence ends, which could push 106 words past 45 s). Every number and name is from the PLOS ONE paper's abstract (doi 10.1371/journal.pone.0105948): the hook says "for decades nobody had seen one move" (the abstract dates speculation to the 1940s; the old "since the 1940s" wording implied someone had seen one before), more than 60 rocks moved on December 20, 2013, ice 3 to 6 mm thick, up to 224 m of travel, a team including Scripps Institution of Oceanography scientists. No individuals are named.
- `tests/conftest.py`: task-aware selection; unknown `LOOM_TASK` is a usage error; heavy tests run only when `CI=true`.
- Tests: `test_schema.py`, `test_conftest_selection.py` (pytester), `voice/test_kokoro.py`, `voice/test_align.py`, `render/test_captions_ass.py`, `render/test_compose.py`, `render/test_qa.py`, `test_render_one.py` (fakes for wiring, heavy golden render), `test_workflows.py` (render.yml), `test_ci_workflow.py`, `test_scope_check.py`. Helpers: `wavs.py`, `media.py`, `workflow_rules.py`.
- `tests/scope_check.py`: the server-side twin of the lock hook. Reads the task YAML and `locks.yaml` from the base ref, diffs with `--no-renames`.
- `.github/workflows/ci.yml`: scope check, LOOM_TASK from the branch (through `env:`, regex-validated), ffmpeg and espeak-ng, all three requirement files, gitleaks and actionlint with sha256 checks, model cache, `make check`, `out/frames/` upload. A `workflow_dispatch`-only `reports` job runs coverage, mutmut, pip-licenses and pip-audit and uploads `out/reports/`.
- `Makefile` (`check`), `.github/dependabot.yml` (pip and actions, weekly), `.gitignore` additions, `.harness/locks.yaml` (`tests/**`, `pipeline/schema.py`, `pipeline/constants.py`, `.github/workflows/ci.yml`, `Makefile`).
- `spec.md` sections 4 and 7: final values and pins. `workflow.md`: criterion to test map with real names, status row.

## Review round 1 fixes
1. CI `git fetch`: already gone at the start of this round (commit 0501d94). `test_ci_workflow` asserts there is no `git fetch` and now also that every checkout has `persist-credentials: false`.
2. `scope_check.py` fails any branch whose `task/` prefix is in another case (`Task/`, `TASK/`), since CI would not set LOOM_TASK for it. The regression test commits only an in-scope file. Wrong comment removed.
3. Kokoro weights pinned: `VOICE_REPO_REVISION` and `VOICE_FILE_SHA256` (config, model, `af_heart`) in constants. The `synthesize` docstring requires `revision=`, a sha256 check before loading, and local paths handed to `KModel` and the voice (kokoro 0.9.4 calls `hf_hub_download` without a revision itself; checked in its source). An unpinned voice raises before any download, now a light test. Format test in `tests/test_pins.py` (owned by no task). The heavy acceptance test checks for the `snapshots/<revision>` folder. The ci.yml cache key is `hashFiles('requirements-heavy.txt', 'pipeline/constants.py')`; `test_workflows.py` requires the same for render.yml. Revision recorded in spec.md section 7.
4. The offline test already ran in a fresh process with `HF_HUB_OFFLINE` set before import, so it did work. It now also refuses every socket connection in that process, so a download by spaCy or misaki fails it too.
5. No index option in any requirements file. Both CI jobs install the `torch==` and `torchaudio==` lines from `--index-url https://download.pytorch.org/whl/cpu` first, then all files from PyPI only. render.yml must do the same (test added).
6. The `en_core_web_sm` URL carries `#sha256=`; a test requires a 64-hex hash on every direct URL.
7. One `ASS_POS` and one `ASS_OVERRIDE` pattern in `tests/media.py`, used by the captions and golden-render tests. `\pos`, `\an` and `\q2` are looked for only inside override blocks, since an escaped word may legally show such text.
8. Captions: `build_ass` must set style Alignment 5, MarginL 54, MarginR 162, event margins 0, no `WrapStyle: 2`, no `\q2` or `\an`, and put the `\pos` x at the safe-zone centre (486) with two font sizes of room above and below. libass wraps every event to the width the margins leave, `\pos` or not (`max_text_width` in `ass_render.c`), so a long line wraps inside the safe zone. Tests check all of it. The hand-written compose captions use the same margins.
9. A light compose test checks that the frame times (1, 4, 8 s) and the last caption end (9.5 s) fall inside the voice fixture. The golden test checks its frame times against the video length.
10. Sample id is `sample-40s`, matching the file (tested). Lines now read "they watched more than 60 rocks move" and "By January, some rocks had travelled up to 224 metres." 99 words.
11. `ADMIN_PATHS` in scope_check is the hook's list verbatim, matched against `"/" + path`, so nested `.claude` folders count too. A drift test reads the hook's list with `ast`, without importing the hook.
12. `ALIGN_MODEL_NAME = "base.en"` in constants; `align_words(audio, text, cache_dir)`; render_one passes its cache dir to both steps. Heavy voice and align tests use `ROOT / render_one.DEFAULT_CACHE_DIR`, the folder CI caches.
- Also: an automated security review of the first round-1 commit found that `git diff --name-only` quotes non-ASCII paths, which would hide a `.claude/hooks/` file from the patterns. The checker now uses `-z`, with a regression test on a non-ASCII hook file name.
- Removed the kokoro-onnx fallback notes from spec.md and this handoff (owner decision). spec.md's pin date corrected to 2026-11-15.

## Review round 2 fixes
1. Tampered weights: `test_tampered_weights_fail_before_kokoro_loads`, parametrized over the three default voice files, tampers one file at a time and expects `VoiceError`, no `out_path`, the file fetched, and no `KModel` or `KPipeline` constructed. The `synthesize` docstring now says all three hashes are checked before anything from kokoro is constructed.
2. Kokoro runtime failure: `test_kokoro_failure_raises_voice_error` makes the fake pipeline raise when called, expects `VoiceError`, no `out_path`, and that the pipeline was called once (so the error came from synthesis). It also checks every download used `VOICE_REPO_ID`, `VOICE_REPO_REVISION` and the given cache dir, which closes the old risk that only the pin format was tested. Both tests use a `fake_kokoro` fixture that puts fake `huggingface_hub` and `kokoro` modules in `sys.modules` and sets the pinned hashes to match the fake files. The docstring names those entry points, rules out a direct torch import and module-level caching. workflow.md's R2 row lists both tests.
3. ci.yml: a missing `origin/$base` now prints `origin/$base not found` before exiting (asserted in `test_ci_scope_check_uses_pr_base_or_main`).
4. torch and torchaudio install with `--no-deps` from the CPU index; torch's dependencies (from the 2.11.0+cpu wheel's `Requires-Dist`, fetched from download.pytorch.org) and theirs are pinned in requirements-heavy.txt and come from PyPI. `workflow_rules.TORCH_INDEX_INSTALL` now includes `--no-deps`, so render.yml must do the same. `test_torch_dependencies_are_pinned` checks the list. spec.md section 7 records the pins and the install order.
5. Sample hook: "for decades nobody had seen one move". 98 words.
- `ALIGN_MODEL_NAME` stays `base.en`: the owner gave no answer on `small.en` in this session.

## Decisions made (and why)
- torch installs with `--no-deps` instead of using a constraints file: the CPU index then supplies only torch and torchaudio, and every other package comes pinned from PyPI, so fewer packages depend on the second index.
- Voice package is `kokoro` 0.9.4 (PyTorch, misaki G2P), confirmed by the owner in review round 1 for voice and timing quality. kokoro leaves transformers, spaCy and the spaCy model loose, so they are pinned, and `en_core_web_sm` is installed from its release wheel so misaki never pip-installs at runtime.
- Whisper model `base.en` for alignment: neither PLAN.md nor spec.md names one. The words come from the script, so the model only supplies timing; base.en is English-only and quick on CPU. Move up a size if alignment drifts.
- Cache keys hash `pipeline/constants.py` instead of repeating the revision literal, so a revision bump cannot leave a stale key.
- torch and torchaudio pinned to 2.11.0 CPU builds: torchaudio has no release past 2.11 and must match torch. stable-ts 2.19.1 calls only `torchaudio.save` (not on the align path) and `torchaudio.functional` filters.
- Round 5: torch stays at 2.11.0 and pip-audit ignores `PYSEC-2025-194` (fixed in torch 2.13.0). Step 1 failed: the newest torchaudio is 2.11.1 on both PyPI and the CPU index. Step 2 failed: stable-ts 2.19.1 imports torchaudio at module level (`stable_whisper/audio/utils.py`, `audio/output.py`, `non_whisper/transcribe.py`), so it cannot be dropped, and a torchaudio built for torch 2.11 is not safe on 2.13. Makefile comment says when to remove the ignore; `test_makefile_ignores_only_the_known_advisories` pins the list at three ids.
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

## Tried and abandoned
- kokoro-onnx as the voice package: lighter, but the owner wants no loss in voice or timing quality.
- The Kokoro revision as a literal in the CI cache key: duplicates the constant and can drift; hashing constants.py covers it.
- torch 2.15.0: no matching torchaudio.
- numpy 2.5: needs Python 3.12; the owner's machine runs 3.11.
- Ruff with `UP` rules and line length 100: flagged existing `.harness/` files this task may not edit.
- Setting `HF_HUB_OFFLINE` with monkeypatch inside the test process: huggingface_hub reads it at import, so the offline test could pass over the network. It now runs the second synthesis in a subprocess.
- The render CLI fake `run_qa` first named its last parameter `words`, which would have failed a correct implementation calling it by keyword; renamed to `script_words`.
- Dropping `.harness/tests` from `make check` to avoid a possible Linux-only failure: it would remove hook coverage from CI, so it stays.
- Two QA alignment cases first broke word order as well as the fault they named, so a QA implementation could pass them for the wrong reason; rewritten to change one thing each.

## Known risks / fragile spots
- Known vulnerability accepted: torch 2.11.0 `PYSEC-2025-194` is ignored in `make check` until a torchaudio for torch 2.13+ ships. Check `pip index versions torchaudio` on each Dependabot cycle; when it exists, move both pins, drop the ignore and update the test.
- Not verified locally, for CI to confirm:
  - All heavy tests (Kokoro, stable-ts, FFmpeg render, QA on real video, golden render). Each is skipped locally by design.
  - The heavy install: the `+cpu` torch wheels from the extra index, kokoro 0.9.4 with transformers 5.22.1 (it imports `AlbertModel` and `AlbertConfig`), spaCy 3.8.18 with the 3.8.0 model, numba's numpy cap. Install time may be long on the first run until the pip cache warms.
  - `make check` itself: bandit, semgrep (`p/python`, ERROR only, scans `tests/` too, which call git and ffmpeg through argument lists), gitleaks on the full history, pip-audit (may skip the `+cpu` packages), actionlint on `ci.yml`.
  - The `reports` job (mutmut 3 config in pyproject).
- Contracts not proven implementable by a reference implementation, mainly `to_word_timings` under the hypothesis property (pieces with arbitrary, even inverted, times must still give clamped monotonic output) and the caption property (End bounds with overlapping timings). I believe both are satisfiable; an implementer who disagrees should write `CONTRACT_CHANGE.md`.
- `escape_ass_text` requires `\{` and `\}`. Current libass (`ass_get_next_char` in `libass/ass_parse.c`) turns both into literal braces, so the contract holds there. The runner's libass may be older, so the compose test's hand-written captions now show `\{10\}` from 6 to 9.5 s; the 8 s frame (`out/frames/compose-008.0s.png`) shows how it renders. The sample script itself has no braces.
- `make check` runs `pytest .harness/tests`, which has only ever run on Windows. If a hook test fails on Linux, the fix is in `.harness/` or `.claude/`, outside this task's scope. I kept it in the gate rather than drop hook coverage.
- semgrep `p/python` at ERROR may flag the list-form `subprocess.run` calls in `tests/` (git, ffmpeg). If it does on the first CI run, narrow the semgrep invocation in this PR's CI round, since the Makefile locks after merge.
- mutmut 3 `also_copy` (queue, .harness, assets) is set from memory of its config options; the first `reports` run confirms it.
- The CI scope check trusts `github.base_ref`, as the owner instructed for stacked PRs. A PR aimed at a weaker base only merges into that base; reaching main still needs a PR against main.
- The compose heavy test's hand-written captions use DejaVu Sans, which `ubuntu-latest` is expected to have.
- On a push run of a stacked branch, the scope check diffs against `origin/main`, as instructed; the PR run (against `github.base_ref`) is the authoritative one.
- An automated security review of the commits flagged two issues, both addressed in the last commit: (1) CI ran the scope checker from the branch, so a branch could edit it. It now runs the copy from the base ref; only the `task/p1-contracts` branch may fall back to its own copy when the base has none, and any other branch fails. A second review round also led to dropping `git fetch` (the checkout has no credentials; `fetch-depth: 0` already provides `origin/*`). `ci.yml` and `Makefile` are now locked too. Still open: a branch can edit `ci.yml` itself and drop the step. The hook blocks that locally and the scope check flags it on later task PRs, but nothing server side stops it on a free private repo without required workflows, so the owner's PR diff review remains the backstop. (2) `Task/x` skipped the check; the prefix is now matched case-insensitively (regression test `test_task_prefix_in_other_case_is_not_skipped`). Non-task branches are still skipped on purpose: the owner's own branches edit harness and admin files.
- Kokoro weights: the light tests now exercise the revision, cache dir and hash checks through fakes. They rely on the docstring's entry points (`hf_hub_download`, `from kokoro import KModel, KPipeline`, no direct torch import). An implementation that imports kokoro differently fails them and should write `CONTRACT_CHANGE.md` rather than work around it. Checked against a throwaway inline reference implementation (not committed): all four new cases pass, and the stub fails them with NotImplementedError.
- `--no-deps` torch install: if the torch 2.11.0+cpu wheel needs a package not in the pinned list, the PyPI step still installs it unpinned; `test_torch_dependencies_are_pinned` holds a hardcoded list that must be updated when torch is bumped. Whether pip accepts the installed torch against these pins is unverified until CI runs. Dependabot will propose `setuptools` 82+ and `mpmath` 1.4+, which break torch's and sympy's upper bounds; those PRs will fail at install and should be closed.
- The `kokoro-v1_0.pth` hash is the Hugging Face LFS sha256 from the API, not hashed locally. `config.json` (2351 bytes) and `af_heart.pt` were downloaded at the pinned revision and hashed, and `af_heart.pt` matched its LFS hash.
- Captions: a single word wider than the 864 px safe width at 96 px cannot wrap and would spill past the edges. Nothing in the sample comes close ("Oceanography" is the longest); a script with a very long word would need a smaller font, and visual-qa should watch for it.
- Captions: the room above and below the `\pos` y (two font sizes) fits three wrapped lines at the default 3 words per line; more words per line could need more.
- The second CI install relies on pip treating the installed `torch==2.11.0+cpu` as satisfied without asking PyPI (which has no `+cpu` build). Standard pip behaviour, unverified until CI runs.
- `pull_request_target` checks stay out of scope by owner decision; the open risk that a branch can edit `ci.yml` itself stands (see the security review item above).

## Next step for whoever picks this up
- Owner pushes `task/p1-contracts` to PR #6 (not pushed in this session) and gets CI green. Fix install or tool-config failures in this task's files; failures in a heavy test of an unbuilt task cannot happen, since those are skipped.
- Gate 2 plus the security specialist review (`ci.yml` matches `.github/workflows/**`).
- Outside this task's `paths_allowed`, for the owner: add `p1-contracts` to `.harness/status.yaml` after merge, update the CLAUDE.md Status line, and consider lessons.md entries: "Writing to the main repo path instead of the worktree path was caught by the hook; always use the worktree root in absolute paths." "Without `-z`, `git diff --name-only` quotes non-ASCII paths, which silently defeats pattern checks." "Python run from a Bash heredoc halves backslashes in non-raw strings (it wrote a NUL byte and a broken `\n` into tests this round); use the Edit tool for code with backslashes."
- Then the five implementer tasks can run in file-name order.

## Docs
- none: no doc states the pip-audit ignore list or the torch pin changes (pins unchanged, spec.md section 7 still correct).

## Evidence
Review round 5, 2026-11-15 (torch vulnerability):
- `pip index versions torchaudio`: newest 2.11.1 (PyPI and CPU index); torch has 2.15.0. Source of stable-ts 2.19.1 checked after `pip download --no-deps`: torchaudio imported at top level. Third option applied.
- `ruff check .`: All checks passed. `mypy --strict pipeline/`: no issues in 11 source files. `pytest --cov=pipeline` (LOOM_TASK=p1-contracts): 100 passed, 110 skipped, 0 failed; coverage 89%. The ignore test caught a missing space between two `--ignore-vuln` flags in the Makefile on the first run. CI pip-audit not run locally (awaiting CI).

Review round 4, 2026-11-15 (pip-audit resolution only):
- Makefile audits a `mktemp` copy of requirements-heavy.txt with `+cpu` stripped via sed (the local versions do not exist on PyPI), same two ignores; `test_makefile_audits_only_project_requirements` updated to match.
- `ruff check .`: All checks passed. `mypy --strict pipeline/`: no issues in 11 source files. `pytest --cov=pipeline`: 100 passed, 110 skipped, 0 failed; coverage 89%. CI pip-audit not run locally (awaiting CI).

Review round 3, 2026-11-15 (pip-audit only):
- Makefile now runs `pip-audit -r requirements.txt -r requirements-heavy.txt`; ci.yml has an "Upgrade build tooling" step (`setuptools>=84.1.0`) before every other install; two tests added to `tests/test_ci_workflow.py`.
- Conflict found and resolved by owner decision: `requirements-heavy.txt` pins `setuptools==81.0.0` (torch needs `<82`), so the later heavy install downgrades the runner's setuptools and pip-audit reads that pin from the file. The Makefile now ignores the two setuptools 81.0.0 advisories (`PYSEC-2026-3447`, `GHSA-xmj3-9gf7-h52w`, found by running pip-audit on that pin) with a comment saying to drop them when torch lifts the cap. Test `test_makefile_ignores_only_the_known_setuptools_advisories` stops the list growing silently.
- `ruff check .`: All checks passed. `mypy --strict pipeline/`: no issues in 11 source files. `pytest --cov=pipeline` (LOOM_TASK=p1-contracts): 99 passed, 110 skipped, 0 failed; coverage 89%.

Review round 2, 2026-11-15:
- `.venv/Scripts/python.exe -m ruff check .`: All checks passed.
- `.venv/Scripts/python.exe -m mypy --strict pipeline/`: Success, no issues found in 11 source files.
- `.venv/Scripts/python.exe -m pytest -q --tb=short --cov=pipeline` (LOOM_TASK=p1-contracts): 97 passed, 110 skipped, 0 failed; coverage 89%.
- `LOOM_TASK=p1-tts-kokoro`, `tests/voice/test_kokoro.py`: 15 failed (all NotImplementedError), 3 skipped (heavy).
- `.venv/Scripts/python.exe -m pytest -q --tb=short .harness/tests`: 51 passed.
- `.venv/Scripts/python.exe tests/scope_check.py task/p1-contracts main` after the round-2 commit: passed, 39 changed files.
- torch and torchaudio 2.11.0+cpu `Requires-Dist` read from the cp312 manylinux wheel `.metadata` files on download.pytorch.org; dependency versions from PyPI's JSON API.

Docs: spec.md section 7 (torch dependency pins, `--no-deps` install order), workflow.md R2 row.

Review round 1, 2026-11-15:
- `.venv/Scripts/python.exe -m ruff check .`: All checks passed.
- `.venv/Scripts/python.exe -m mypy --strict pipeline/`: Success, no issues found in 11 source files.
- `.venv/Scripts/python.exe -m pytest -q --tb=short --cov=pipeline` (LOOM_TASK=p1-contracts): 96 passed, 106 skipped, 0 failed; coverage 89% of the stubs.
- Each task's tests against the stubs with `LOOM_TASK` set to that task: no collection errors; every non-heavy test fails with NotImplementedError (render.yml tests with FileNotFoundError) and heavy tests skip. tts-kokoro 11 failed, 3 skipped; align 8 failed, 3 skipped; captions-ass 26 failed, 1 passed (purity guard); compose 6 failed, 2 passed (shell guard, fixture timing), 3 skipped; qa 21 failed, 3 skipped; render-cli 11 failed, 1 skipped; actions-workflow 7 failed.
- `.venv/Scripts/python.exe tests/scope_check.py task/p1-contracts main`: scope check passed, 39 changed files.
- Hugging Face API for `hexgrad/Kokoro-82M` main gave sha `f3ff3571791e39611d31c381e3a41a3af07b4987`; file hashes as in constants.py. The spaCy wheel was downloaded and hashed.
- `.venv/Scripts/python.exe -m pytest -q --tb=short .harness/tests`: 51 passed.
- Local venv has only requirements.txt and requirements-dev.txt; no heavy packages installed.
