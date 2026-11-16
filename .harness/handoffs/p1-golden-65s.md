# Handoff: p1-golden-65s

## Goal
The "Extract golden frames" step in `.github/workflows/render.yml` uses the shared helper `media.extract_golden_frames`, so the render artifact shows the full 65 s video including the end frame.

## Status
done. Branch `task/p1-golden-65s`, committed, not pushed.

## What changed (and why)
- `.github/workflows/render.yml`: the run line of "Extract golden frames" now calls `media.extract_golden_frames(Path('out/render/final.mp4'))`. The `pipeline.constants` import is gone because the helper owns the times. Step name and `if:` condition are unchanged. One helper means the heavy test and the workflow cannot drift apart.

## Decisions made
- None beyond the task YAML.

## Tried and abandoned
none

## Known risks
- The end frame seeks to `duration - 0.5` s in CI for the first time (the heavy test does the same, awaiting CI). A bad seek would fail the step with `CalledProcessError`.
- Workflow change, so the security specialist review runs with Gate 2. The command is a fixed string with no user input and no shell interpolation.

## Next step
Gate 2 review plus security review, then merge. Optionally run render.yml once after merge and check the `frames` artifact holds eight golden frames (1 s to 60 s plus the end).

## Docs
none. The Architect handoff already lists the doc updates (workflow.md, architecture.md, orchestrator.md, status.yaml at close-out); this change needs nothing beyond those.

## Evidence
- `LOOM_TASK=p1-golden-65s pytest -q`: 325 passed, 14 skipped (heavy tests, awaiting CI).
- `pytest tests/test_golden_frames.py tests/test_workflows.py tests/test_render_default.py`: 9 passed.
- `ruff check .`: all checks passed. `python tests/docs_check.py`: passed.
- `mypy --strict pipeline/` not run: no pipeline code changed.
