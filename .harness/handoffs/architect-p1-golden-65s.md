# Handoff: architect-p1-golden-65s

## Goal
The heavy golden render renders the 65 s sample, but `GOLDEN_FRAME_TIMES_S` stopped at 30 s, so only the first half of the video was ever looked at. Extend the golden frames over the full length, including the end, keep CI timeout headroom, decide how golden frames are produced, and plan the implementer task.

## Status
done. Branch `docs/p1-golden-65s-contracts`, committed, not pushed.

## What changed (and why)
- `pipeline/constants.py` (locked): `GOLDEN_FRAME_TIMES_S` is now (1, 10, 20, 30, 40, 50, 60) and a new `GOLDEN_END_OFFSET_S` is 0.5. A fixed time must stay below 62 s (`TIKTOK_SECONDS[0]`), because that is all QA guarantees about length; the approved video ran 69.6 s, so the last stretch can only be reached by a frame placed relative to the end.
- `tests/media.py` (locked): new `extract_golden_frames(video)`, the fixed times plus one frame `GOLDEN_END_OFFSET_S` before the container's end (`duration()`). The heavy test already pins container vs voice drift to 0.2 s, and compose uses `-shortest`, so 0.5 s stays inside the last video frame. One helper, so the heavy test and render.yml cannot drift apart.
- `tests/test_render_one.py` (locked, owned by the done task p1-render-cli, so it runs on main):
  - Heavy `test_acceptance` calls the helper, expects one frame per fixed time plus the end frame, and probes each PNG for 1080x1920 (a missing or empty frame fails the probe).
  - New light `test_golden_frames_span_every_video_that_passes_qa`: times sorted and unique, the last one below the shortest QA-passing length minus the end offset, and no gap over 10 s from 0 s to 62 s. Stops the tuple going invalid later.
- `tests/test_golden_frames.py` (new, owned by p1-golden-65s): acceptance checks render.yml calls `media.extract_golden_frames(` and no longer names `GOLDEN_FRAME_TIMES_S`.
- `.harness/tasks/phase1/20_golden_65s.yaml`: implementer task p1-golden-65s, one line in `.github/workflows/render.yml`. Without it the render artifact would keep the old fixed frames and never show the end.

## Decisions made
- No committed reference images and no pixel comparison. In this repo "golden frames" are frames extracted for the visual-qa reviewer to look at, never diffed; nothing in PLAN.md, spec.md or architecture.md asks for a diff. A diff would also be flaky: ffmpeg, libass and x264 come from apt on `ubuntu-latest` (not pinned), and CPU torch is not guaranteed bit-exact, so the voice timing can shift a frame. So nothing has to be captured and committed, unlike the FFmpeg text fixtures. Frames come from every CI heavy run (`frames` artifact, `if: always()`, 7 days) and every render.yml run (`frames` artifact, 3 days).
- No frames past 60 s other than the end frame. For the 69.6 s sample the largest gap is 60 s to 69.1 s. A 90 s video would have a 29.5 s unsampled stretch; the golden test only renders the sample, so a duration-based grid is not worth it now.
- The light invariant lives in `test_render_one.py` (done task), not in the new file, so it protects main before p1-golden-65s is done.
- One implementer task for the render.yml line. The heavy test already uses the helper, so the golden render itself needs no implementer work.

## Tried and abandoned
- End frame from the video stream's own `duration` key. Dropped: the only real ffprobe capture in the repo (`tests/fixtures/ffmpeg/ffprobe_video.json`) was taken with a narrow field selection, so it cannot confirm the key exists, and a missing key would raise `KeyError` in CI. The container duration is always present.

## Known risks
- Heavy test not run locally (no ffmpeg or torch by rule), awaiting CI. The end-frame seek and the PNG probe are new; if ffmpeg wrote no PNG at `duration - 0.5`, the probe would fail with `CalledProcessError` in the first CI run.
- Timeout headroom: render step 125 s in run 43873059742 against the test's 1200 s subprocess timeout; recent CI runs take 5 to 8 minutes against `timeout-minutes: 45`. Four extra frames are four single-frame ffmpeg calls, a few seconds. Editing `constants.py` changes the model cache key in ci.yml and render.yml (`hashFiles(..., 'pipeline/constants.py')`), so the first run downloads the weights cold; still well inside 45 minutes.
- Visual QA is not triggered automatically: `specialist_reviews.visual_qa` matches `pipeline/render/**`, `pipeline/visuals/**` and `assets/**`, and none of this work touches them. It has to be run by hand (next step).

## Next step
1. Orchestrator pushes `docs/p1-golden-65s-contracts` and opens the PR. The CI heavy run on it renders the 65 s sample and uploads the new frames. Owner merges after CI is green and visual QA (step 2) is clean.
2. Visual QA on that run: `gh run download <ci-run-id> -n frames -D out/frames`, then run the `visual-qa` agent on `out/frames/golden-*.png` (eight frames, 1 s to 60 s plus the end). It checks the late captions and the end frame, which no review has seen yet. Not a CI capture-and-commit step: nothing goes into the repo.
3. Orchestrator runs p1-golden-65s as an implementer task (Sonnet), `LOOM_TASK=p1-golden-65s`. render.yml change, so the security specialist review runs with Gate 2. Optionally the owner runs render.yml once after merge to confirm the artifact has the end frame.
4. Then p1-phase-review (task 14).

## Docs
- PRD.md: applied on this branch, a 2026-11-16 decision entry (golden frames cover the whole video; visual review, no committed or pixel-compared references, and why).
- spec.md: none (no mention of golden frames).
- workflow.md (not edited here, PR #52 touches it): add a status row "p1-golden-65s, not started"; the R6.2 row should read "writes `out/frames/golden-*.png`, 1 s to 60 s plus one frame 0.5 s before the end".
- architecture.md (not edited here, PR #52 touches it): wherever the golden render or render.yml frame step is described, say both use `tests/media.py::extract_golden_frames`, and that golden frames are for visual review, not pixel comparison.
- orchestrator.md: the follow-up "extend GOLDEN_FRAME_TIMES_S past 30 s" is done by this branch; replace it with the visual-qa step above.
- status.yaml: add p1-golden-65s to `done` at its close-out (not now).

## Evidence
Local, Windows, venv in the worktree with requirements.txt and requirements-dev.txt only:
- `ruff check .`: all checks passed. `mypy --strict pipeline/`: no issues. `python tests/docs_check.py`: passed.
- `pytest` without `LOOM_TASK`: 312 passed, 27 skipped (new task file and heavy tests skipped; the new light invariant passes).
- `pytest` with `LOOM_TASK=p1-golden-65s`: 1 failed, 312 passed, 26 skipped. The failure is `tests/test_golden_frames.py::test_acceptance`, as expected (render.yml still calls `extract_frames` with the fixed times).
- Passable: a throwaway one-line render.yml change made `test_golden_frames.py`, `test_workflows.py` and `test_render_default.py` pass (9 passed). Reverted, not committed.
