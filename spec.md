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

Import rule: `schema` and `constants` import nothing from `pipeline`. Modules under `voice/` and `render/` import only those two, never each other. `render_one.py` is the only file that imports the modules. Details in architecture.md section 2.

## 3. Data model

**Script** (one JSON file per video, PLAN.md section 7): `id`, `topic`, `template` (`chart | map | steps | story`), `hook`, `scenes[]`, `loop_line`, `title`, `description`, `tags[]`, `platforms[]`, `publish_after` (ISO date). Each scene has `narration`, `on_screen_text`, `visual` (`type`, `data`) and `source_fact_ids[]`. Phase 1 reads `hook`, the scene narrations and `loop_line`; visual fields are validated but not rendered yet.

Narration text for voice and alignment is `hook`, then each scene's `narration`, then `loop_line`, joined by single spaces.

**WordTiming**: `word` (exact script token), `start`, `end` (seconds, float).

**QAReport**: `passed` (bool), `failures[]` of `{check, reason}`, `measured` (dict of the values checked).

Scripts move between `queue/approved/` and `queue/published/` as plain files. A schema change bumps a `schema_version` field and needs a contract change approved by the Architect.

## 4. Rules and numbers

All of these live in `pipeline/constants.py` and nowhere else.

| Rule | Value | Source |
|---|---|---|
| Resolution, frame rate | 1080x1920, 30 fps | PLAN.md section 2 |
| Loudness | -14 LUFS integrated, tolerance 1 LU | PLAN.md section 2 |
| Speech rate | about 160 wpm | PLAN.md section 4 |
| Retention format | 25 to 45 s, 70 to 120 words | PLAN.md section 4 |
| TikTok format | 61 to 90 s, 165 to 230 words, QA minimum 62 s | PLAN.md section 4 |
| Longest allowed silence | 1.5 s | PLAN.md section 7 |
| Caption safe zone | Nothing in the top 15%, bottom 25% or right 15% of the frame, plus a 5% left margin: x from 54 to 918 px, y from 288 to 1440 px | Platform UI overlap |
| File size range | 100 KB to 100 MB. Smaller means an empty or broken render; the top is far below every platform's upload limit | PLAN.md section 7 |
| Voice | Kokoro-82M, voice `af_heart`, speed 1.0, mono wav at 24 kHz; silent if the peak stays below 0.01 of full scale | Kokoro's native output |
| Voice length check | Within 40% of the word count's duration at 160 wpm | R2.1 |
| Alignment slack | Word timings may end up to 0.05 s past the voice | Rounding |

Never allowed: a render that continues after voice failure, an empty or silent wav, a caption word that differs from the script word.

## 5. Security and privacy design

- Secrets only in GitHub Actions encrypted secrets. Phase 1 needs none.
- Subprocess calls (FFmpeg, ffprobe) take an argument list. `shell=True` is never used.
- Third-party GitHub Actions are pinned to a full commit SHA.
- Python dependencies are pinned to exact versions.
- No personal details in code, config, commits or logs.

## 6. Quality gates

Gate 1, before any review (HARNESS.md sections 6a and 6b), is `make check` in CI: ruff, `mypy --strict pipeline/`, `pytest --cov=pipeline`, bandit, semgrep, gitleaks, pip-audit and actionlint. Any high-severity finding fails it. Locally (Windows, no make) run the light part:

```
ruff check .
mypy --strict pipeline/
pytest --cov=pipeline
```

Coverage must not drop. Harness tests run separately: `pytest .harness/tests`.

`tests/conftest.py` skips a task's tests until the task is in `.harness/status.yaml` or is the current `LOOM_TASK`. Tests marked `heavy` (ffmpeg, torch, Kokoro) run only in CI; locally they skip. So Gate 1 for a heavy task means a green CI run on its `task/<task-id>` branch.

## 7. Approved dependencies

Pinned by p1-contracts on 2026-11-15 to the newest stable release at least two weeks old. The pins live in three files so the local install stays light:

- `requirements.txt` (runtime, light): `pydantic` 2.14.2, `pyyaml` 6.0.3, `soundfile` 0.14.0, `numpy` 2.4.6 (2.5 needs Python 3.12).
- `requirements-dev.txt`: `pytest` 9.2.0, `pytest-cov` 7.1.0, `hypothesis` 6.170.14, `ruff` 0.17.3, `mypy` 2.4.1, `types-PyYAML` 6.0.12.20261030, `bandit` 1.9.4, `pip-audit` 2.10.1, `pip-licenses` 5.5.5, and on Linux only `semgrep` 1.183.0 and `mutmut` 3.8.1.
- `requirements-heavy.txt` (CI and the render workflow only, never local): `torch` and `torchaudio` 2.11.0 CPU builds (torchaudio's last release line, and the two must match), `stable-ts` 2.19.1, `openai-whisper` 20250625, `kokoro` 0.9.4, `misaki[en]` 0.9.4, plus pins for what kokoro leaves loose: `transformers` 5.22.1, `spacy` 3.8.18 and the `en_core_web_sm` 3.8.0 model (misaki would otherwise download it at runtime).
- CI binaries, checksum verified in `ci.yml`: `gitleaks` 8.30.1, `actionlint` 1.7.12.
- System: `ffmpeg` and `espeak-ng` (apt).

Voice package: `kokoro` (PyTorch, misaki G2P), by owner decision, for voice and timing quality. Weights come from the Hugging Face repo `hexgrad/Kokoro-82M` at commit `f3ff3571791e39611d31c381e3a41a3af07b4987` (`VOICE_REPO_REVISION`) into the cache folder the caller passes, and each loaded file (`config.json`, `kokoro-v1_0.pth`, `voices/af_heart.pt`) is checked against its sha256 in `VOICE_FILE_SHA256` before use. Alignment uses the whisper `base.en` model (`ALIGN_MODEL_NAME`), downloaded into the same cache folder; openai-whisper checks its sha256 itself.

Install order: CI installs `torch` and `torchaudio` from the PyTorch CPU index alone (`--index-url https://download.pytorch.org/whl/cpu`), then every requirements file from PyPI alone. No requirements file names an extra index, so no package can be resolved from both. Direct wheel URLs carry a `#sha256=` fragment.

Anything else needs owner approval first.
