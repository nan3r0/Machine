# Handoff: p1-sample-65s

## Goal
Make `queue/approved/sample-65s.json` the default `script` input of the render workflow.

## Status
partial, awaiting owner manual acceptance. The locked test passes locally. The owner still has to run the workflow on GitHub with the default input and approve the downloaded 65 s `final.mp4`. Whether the voice reaches the 62 s QA minimum is not known until that run.

## What changed (and why)
- `.github/workflows/render.yml`: the `script` input default changed from `queue/approved/sample-40s.json` to `queue/approved/sample-65s.json` (owner decision 2026-11-16, every video about 65 s). Nothing else in the workflow changed.

## Decisions made
- Kept `queue/approved/sample-40s.json`, as the task says: the locked heavy golden test renders it.
- No owner decision was changed.

## Tried and abandoned
none

## Known risks
- If Kokoro voices the script in under 62 s, QA fails. The task says to report that here and not edit the script; nothing has been measured yet.
- A workflow file changed, so the security specialist review runs.

## Next step
Gate 1 in CI, then the security review, then the owner runs the workflow on GitHub and approves the 65 s video.

## Docs
- `CLAUDE.md` Status: after the owner approves the 65 s video, add p1-sample-65s to Done and note that the default sample is 65 s.
- `workflow.md`: mark p1-sample-65s done after the same approval.
- `lessons.md`: none needed from this task. Evidence note: the shadowed `tests` package (existing lessons.md entry, 2026-11-15) hit again, see Evidence.
- `spec.md` / `architecture.md`: none.

## Evidence
- `tests/test_render_default.py::test_acceptance`, `tests/test_ci_workflow.py` and `tests/test_workflows.py`: 26 passed.
- `python tests/docs_check.py`: passed.
- Shim needed: the repo has no `tests/__init__.py`, so the site-packages `tests` package wins on import. I ran pytest from a small `python -c` runner that registers the repo `tests` folder as the `tests` module first.
