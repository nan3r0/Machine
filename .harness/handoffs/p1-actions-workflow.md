# Handoff: p1-actions-workflow

## Goal
Add `.github/workflows/render.yml`: manual run that renders a script JSON with `pipeline.render_one` and uploads the output and golden frames.

## Status
partial, awaiting CI and the owner's manual check. The 7 structure tests in `tests/test_workflows.py` pass locally. actionlint is not installed here, so it has not run; CI's Gate 1 runs it. The real render run on GitHub is the owner's manual acceptance.

## What changed (and why)
- `.github/workflows/render.yml` (new): `workflow_dispatch` only, with a `script` input (default `queue/approved/sample-40s.json`). One job on `ubuntu-latest`, `permissions: contents: read`, no secrets, 45 minute timeout.
  - Steps: checkout (no persisted credentials), setup-python 3.12 with pip cache, apt `ffmpeg espeak-ng`, torch from the PyTorch CPU index alone then `requirements.txt` and `requirements-heavy.txt`, model cache on `.cache/models`, render, golden frame extraction, two uploads.
  - Action SHAs, the torch install and the model cache key (`requirements-heavy.txt` plus `pipeline/constants.py`) are copied from `ci.yml`.
  - The script input reaches the CLI through the step's `env` (`SCRIPT_PATH`), never inside `run:`.
  - Output goes to `out/render` (`final.mp4`, `qa.json`, logs, wav, captions). The `render` artifact and the `frames` artifact both keep 3 days and fail if empty.

## Decisions made
- The render CLI does not extract frames, only the heavy test does. The workflow extracts them after the render by calling `tests.media.extract_frames` with `constants.GOLDEN_FRAME_TIMES_S`, so the times stay in `constants.py` and no helper is duplicated.
- Frame extraction and both uploads run when the job is not cancelled and the files exist, so a QA failure (exit 1) still uploads the video and frames for inspection.
- `requirements-dev.txt` is not installed: the render needs only `requirements.txt` and `requirements-heavy.txt`, and `tests/media.py` uses the stdlib. If CI shows it imports something from dev, add it.
- No owner decision was changed.

## Tried and abandoned
- Job-level `env` for `SCRIPT_PATH`: the locked test looks for `inputs.script` in the render step's own `env`, so it moved to the step.

## Known risks
- Not run on GitHub yet. First real run may expose the pip, torch or weight download steps (see the pip-audit lesson: run a CI tool once before locking it).
- `python -c` in the frame step relies on the repo root being on `sys.path` (the working directory is) and on `tests` being a namespace package.
- Locally, pytest needs the `tests` module shim because a `tests` package in site-packages shadows the repo's.

## Next step
Push. CI runs actionlint and the structure tests. Then the security specialist review (workflow trigger). Then the owner runs the workflow from the Actions tab and approves the downloaded `final.mp4`.

## Docs
- `CLAUDE.md` Status: move p1-actions-workflow to Done only after CI is green, the review passes and the owner approves the run.
- `workflow.md`: p1-actions-workflow done only after the manual check.
- `architecture.md` / `spec.md`: render workflow is manual-only (`workflow_dispatch`, input `script`), output to `out/render`, artifacts `render` and `frames` kept 3 days, golden frames extracted in the workflow. Applied at close-out.
- `lessons.md`: none.

## Evidence
- `tests/test_workflows.py` and `tests/test_ci_workflow.py` via the `tests` shim: 25 passed.
- First run had 1 failure (env on the job, not the step); fixed and re-run green.
