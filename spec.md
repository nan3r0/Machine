# Shorts Pipeline: Technical Spec

Tool choices and their free limits are in PLAN.md section 3. This file holds what code needs to agree on.

## 1. Stack

- Python 3.11+ (CI runs 3.12 on `ubuntu-latest`).
- GitHub Actions for all scheduled and manual runs.
- FFmpeg (apt package on the runner) for render, probe, loudness and silence detection.
- pytest for tests, ruff for lint, mypy `--strict` for types on `pipeline/`.

## 2. Project layout

Follows PLAN.md section 9. Phase 1 adds:

```
pipeline/schema.py        # Pydantic models (locked contract)
pipeline/constants.py     # render and QA numbers (locked contract)
pipeline/render_one.py    # entry point: one script JSON to final.mp4
tests/conftest.py         # task-aware test selection (locked)
tests/                    # mirrors pipeline/, plus tests/fixtures/
.harness/status.yaml      # tasks that passed all gates; edited by the owner only
.harness/  .claude/       # build harness, see HARNESS.md section 11
```

Phase 2 adds (stubs with docstring contracts from p2-contracts; `factcheck/normalise.py` and `exact.py` done):

```
pipeline/factcheck/normalise.py, exact.py   # exact layer: numbers and proper nouns
pipeline/factcheck/semantic.py              # meaning layer: one checker call per script
pipeline/script/validate.py                 # publishable-field and word-count checks
pipeline/script/gemini.py                   # the only file that talks to Gemini
pipeline/script/sources.py, generate.py     # pick unused sources, write a script
pipeline/script/prompt_data.py              # shared untrusted-text cleaning and delimiters for prompts
pipeline/script/batch.py                    # entry point of Workflow A
sources/<slug>.yaml                         # hand-curated facts, one solved mystery each
.github/workflows/weekly_scripts.yml        # Workflow A
```

Import rule: `schema` and `constants` import nothing from `pipeline`. Modules under `voice/` and `render/` import only those two, never each other. `render_one.py` is the only file that imports the modules. Details in architecture.md section 2.

## 3. Data model

**Script** (one JSON file per video, PLAN.md section 7): `id`, `topic`, `template` (`chart | map | steps | story`), `hook`, `scenes[]`, `loop_line`, `title`, `description`, `tags[]`, `platforms[]`, `publish_after` (ISO date). Each scene has `narration`, `on_screen_text`, `visual` (`type`, `data`) and `source_fact_ids[]`. Phase 1 reads `hook`, the scene narrations and `loop_line`; visual fields are validated but not rendered yet.

Narration text for voice and alignment is `hook`, then each scene's `narration`, then `loop_line`, joined by single spaces.

**WordTiming**: `word` (exact script token), `start`, `end` (seconds, float).

**QAReport**: `passed` (bool), `failures[]` of `{check, reason}`, `measured` (dict of the values checked).

**Source file** (Phase 2, `sources/<slug>.yaml`, `SourceFile` in `schema.py`): `topic`, `facts[]` of `{id, text, url}`. Fact ids are integers unique across all source files, urls are https. Topics are unique ignoring case and punctuation. The slug is a lowercase hyphenated name and becomes the script id. A script's `source_fact_ids` come from one source file. A source is "used" once any of its fact ids appears in a script under `queue/` (approved or published); the queue files are the ledger (owner decision D3, no `data/used_facts.json`). The Phase 1 sample cites facts 1 to 9, which the Bloop source holds; seeded sources use blocks of 100 from 101.

**Flag**: `script_id`, `scene` (index, or none for the whole script), `reason`. Flags go into the PR body, never into the script file. **LineVerdict**: `index`, `verdict` (`SUPPORTED | UNSUPPORTED | PARTIAL`), `reason`, `fact_ids`; SUPPORTED and PARTIAL must name at least one fact id.

Scripts move between `queue/approved/` and `queue/published/` as plain files. `queue/published/` is append-only: a published script is never edited or deleted, so its sources stay used. Workflow A writes new scripts straight into `queue/approved/` on its PR branch, so merging the PR is the approval (owner decision D2; no `queue/pending/`, no `on_merge_approve.yml`). A schema change bumps a `schema_version` field and needs a contract change approved by the Architect.

## 4. Rules and numbers

All of these live in `pipeline/constants.py` and nowhere else.

| Rule | Value | Source |
|---|---|---|
| Resolution, frame rate | 1080x1920, 30 fps | PLAN.md section 2 |
| Loudness | -14 LUFS integrated, tolerance 1 LU | PLAN.md section 2 |
| Speech rate | 144 wpm (measured: 167 words in 69.5 s at speed 0.9, render run 43873059742) | PLAN.md section 4 |
| 65 s format (the only format: every video is over a minute; `TIKTOK_*` in code) | Target about 65 s and 156 words; accepted 62 to 90 s and 149 to 216 words (the seconds at 144 wpm, rounded inwards) | PLAN.md section 4 |
| Longest allowed silence | 1.5 s | PLAN.md section 7 |
| Caption safe zone | Nothing in the top 15%, bottom 25% or right 15% of the frame, plus a 5% left margin: x from 54 to 918 px, y from 288 to 1440 px | Platform UI overlap |
| File size range | 100 KB to 100 MB. Smaller means an empty or broken render; the top is far below every platform's upload limit | PLAN.md section 7 |
| Voice | Kokoro-82M, voice `af_heart`, speed 0.9, mono wav at 24 kHz; silent if the peak stays below 0.01 of full scale | Kokoro's native output |
| Voice length check | Within 40% of the word count's duration at 144 wpm | R2.1 |
| Alignment slack | Word timings may end up to 0.05 s past the voice | Rounding |
| FFmpeg render | Audio 48 kHz, true peak -1 dBTP, 600 s timeout per FFmpeg call, last 20 stderr lines in errors | Player support, loudnorm linear mode, run 43873059742 |
| QA tools | fps tolerance 0.01, 300 s timeout per ffprobe or silencedetect call, last 5 stderr lines in errors | |

Phase 2 numbers (owner decisions D5 and D6):

| Rule | Value | Source |
|---|---|---|
| Scripts per batch | 7 | PLAN.md section 11 |
| Word target | 156 (65 s at 144 wpm) inside the accepted 149 to 216 | PLAN.md section 4 |
| Writer and checker models | Writer `gemini-3.8-flash`, checker `gemini-3.5-flash-lite` at temperature 0; never a `gemini-2.5-*` or preview model. Model ids retire: someone checks the Gemini deprecations page every few months | D5, PRD.md section 7 |
| Model calls per batch | At most 14 writer and 14 checker calls (7 scripts plus one retry or rewrite each), counted as made. The caps count logical calls: the client's one retry means each call can make 2 HTTP requests, so a run makes up to 28 HTTP requests per model, and each model's free daily limit must cover 28. Runs of `weekly_scripts.yml` never overlap (concurrency group `weekly-scripts`, CSO P2-6). 120 s timeout per call; one retry after 10 s on HTTP 429, a 5xx or a timeout; HTTP 404 (retired model) fails at once | PLAN.md section 3 |
| Published fields | Title up to 100 characters (YouTube's limit), description up to 1000, at most 10 tags of up to 30 characters, 500 in total; no URLs, `<` or `>` anywhere | CSO P1-3, D6 |
| Script and source size | At most 10 scenes and 1500 characters of narration; at most 10 facts per source, fact text up to 160 characters and url up to 100; reasons clipped to 120 | Keeps the PR body under its cap |
| PR body | Up to 60000 characters (GitHub caps a body at 65536); 7 scripts at every cap come to about 48500 plus layout | R13.1 |

Never allowed: a render that continues after voice failure, an empty or silent wav, a caption word that differs from the script word.

## 5. Security and privacy design

- Secrets only in GitHub Actions encrypted secrets. Phase 1 needs none. Phase 2 needs one, `GEMINI_API_KEY`: a repo secret (D1 option (c), decided 2026-11-18, PRD.md section 7), from an AI Studio project with no billing. It reaches no unpinned install: Workflow A stays disabled until p2-weekly-hardening (CSO P2-1) has merged. It is read from the environment at call time, sent only in the `x-goog-api-key` header, and never logged or put in an exception. Only the `generate` job of `weekly_scripts.yml` gets it; that job has a read-only token. Restrict the key in Google Cloud to the Generative Language API.
- Text from sources and from the model is untrusted: source facts go into prompts as delimited data, model output is parsed and validated before use, and branch names, PR titles and commit messages never come from model output.
- In the approval PR body every model-derived string (flag and left-out reasons, hook, narration, loop line, title, description, tags) sits inside a fenced code block or a same-line code span whose fence is longer than any backtick run in the text. No link, image, HTML tag or comment, and no @mention (GitHub notifies on a bare @name), can come from the model. Only fact texts and urls (owner-reviewed), script ids and fixed labels are plain Markdown.
- The Gemini client fails loudly: HTTP 404 (usually a retired model id) and a second 429 raise at once; there is never more than one retry.
- Subprocess calls (FFmpeg, ffprobe) take an argument list. `shell=True` is never used.
- Third-party GitHub Actions are pinned to a full commit SHA.
- Python dependencies are pinned to exact versions.
- No personal details in code, config, commits or logs.

## 6. Quality gates

Gate 1, before any review (HARNESS.md sections 6a and 6b), is `make check` in CI: ruff, `mypy --strict pipeline/`, `pytest --cov=pipeline`, the docs check (`tests/docs_check.py`), bandit, semgrep, gitleaks, pip-audit and actionlint. Any high-severity finding fails it. Locally (Windows, no make) run the light part:

```
ruff check .
mypy --strict pipeline/
pytest --cov=pipeline
```

Coverage must not drop. Harness tests run separately: `pytest .harness/tests`.

`tests/conftest.py` skips a task's tests until the task is in `.harness/status.yaml` or is the current `LOOM_TASK`. Tests marked `heavy` (ffmpeg, torch, Kokoro) run only in CI; locally they skip. So Gate 1 for a heavy task means a green CI run on its `task/<task-id>` branch.

## 7. Approved dependencies

Pinned by p1-contracts on 2026-11-15 to the newest stable release at least two weeks old. The pins live in four files so the local install stays light:

- `requirements-generate.txt` (Workflow A's `generate` job): every direct pin from `requirements.txt` plus six transitive packages, each with a sha256 line, installed with `--require-hashes`. Regenerate it whenever `requirements.txt` changes; the pin test fails until then.
- `requirements.txt` (runtime, light): `pydantic` 2.14.2, `pyyaml` 6.0.3, `soundfile` 0.14.0, `numpy` 2.4.6 (2.5 needs Python 3.12).
- `requirements-dev.txt`: `pytest` 9.2.0, `pytest-cov` 7.1.0, `hypothesis` 6.170.15, `ruff` 0.17.5, `mypy` 2.4.1, `types-PyYAML` 6.0.12.20261030, `bandit` 1.9.4, `pip-audit` 2.10.1, `pip-licenses` 5.5.5, and on Linux only `semgrep` 1.183.0 and `mutmut` 3.8.1.
- `requirements-heavy.txt` (CI and the render workflow only, never local): `torch` and `torchaudio` 2.11.0 CPU builds (torchaudio's last release line, and the two must match), `stable-ts` 2.19.1, `openai-whisper` 20250625, `kokoro` 0.9.4, `misaki[en]` 0.9.4, plus pins for what kokoro leaves loose: `transformers` 5.22.1, `spacy` 3.8.18 and the `en_core_web_sm` 3.8.0 model (misaki would otherwise download it at runtime). torch's own dependencies, taken from the CPU wheel's metadata, are pinned too: `filelock` 4.2.10, `typing-extensions` 4.16.0, `setuptools` 81.0.0 (torch needs below 82), `sympy` 1.14.0 with `mpmath` 1.3.0 (sympy needs below 1.4), `networkx` 3.7, `jinja2` 3.1.6 with `markupsafe` 3.0.4, `fsspec` 2026.9.0. torchaudio declares no dependencies.
- CI binaries, checksum verified in `ci.yml`: `gitleaks` 8.30.1, `actionlint` 1.7.12.
- System: `ffmpeg` and `espeak-ng` (apt).
- Licence note, `espeakng-loader` 0.2.4 (pulled in by `misaki[en]`, checked 2026-11-22): the release has no licence. Its commit [`146599e`](https://github.com/thewh1teagle/espeakng-loader/tree/146599e29be31bf17d99f0bcb7dbb2f92aef3d95) has no LICENSE file and the wheel has no licence metadata. The author added an [MIT LICENSE](https://github.com/thewh1teagle/espeakng-loader/blob/main/LICENSE) later (commit `0ddc87a`, 2025-11-01), and 0.2.4 is still the latest release on PyPI. The manylinux x86_64 wheel bundles `libespeak-ng.so.1.52.0` and `espeak-ng-data/`, which are [GPL-3.0](https://github.com/espeak-ng/espeak-ng). Nothing forbids commercial use, and GPL duties apply only to distribution, which this private pipeline does not do, so this is a note, not a go-live blocker. Re-check if the repo or an image containing these files is ever distributed.

Voice package: `kokoro` (PyTorch, misaki G2P), by owner decision, for voice and timing quality. Weights come from the Hugging Face repo `hexgrad/Kokoro-82M` at commit `f3ff3571791e39611d31c381e3a41a3af07b4987` (`VOICE_REPO_REVISION`) into the cache folder the caller passes, and each loaded file (`config.json`, `kokoro-v1_0.pth`, `voices/af_heart.pt`) is checked against its sha256 in `VOICE_FILE_SHA256` before use. Alignment uses the whisper `small.en` model (`ALIGN_MODEL_NAME`), downloaded into the same cache folder; openai-whisper checks its sha256 itself.

Install order: CI installs `torch` and `torchaudio` from the PyTorch CPU index alone and without their dependencies (`--no-deps --index-url https://download.pytorch.org/whl/cpu`), then every requirements file from PyPI alone. No requirements file names an extra index, so no package can be resolved from both. Direct wheel URLs carry a `#sha256=` fragment.

Phase 2 adds no dependency: the Gemini client uses the standard library (`urllib.request`, `json`), and the fact-check is plain Python.

Anything else needs owner approval first.
