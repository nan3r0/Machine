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
| Caption safe zone | Proposed: nothing in the top 15%, bottom 25% or right 15% of the frame. Final values set by p1-contracts | Platform UI overlap |
| File size range | Set by p1-contracts | PLAN.md section 7 |

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

Exact versions are pinned by p1-contracts after checking current releases.

Runtime: `pydantic`, `pyyaml`, `kokoro` (or `kokoro-onnx` if lighter on CPU; p1-contracts decides and notes why), `stable-ts` (brings `torch` CPU build and `openai-whisper`), `soundfile`, `numpy`.
Dev: `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`, `types-PyYAML`.
CI only (HARNESS.md section 6b): `bandit`, `semgrep`, `pip-audit`, `pip-licenses`, `mutmut`, plus `gitleaks` and `actionlint` binaries pinned by version.
System: `ffmpeg` (apt), `espeak-ng` if Kokoro needs it.

Anything else needs owner approval first.
