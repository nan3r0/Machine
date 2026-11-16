# Handoff: architect-p1-constants-timeout

## Goal
Before Phase 2 scripts (owner-approved plan, 2026-11-16): set the speech rate to the measured 144 wpm and re-derive `TIKTOK_WORDS`; move the numbers private to `compose.py` and `qa.py` into `pipeline/constants.py`; give `compose._run_ffmpeg` a timeout. Write the constants change and the locked tests, and plan the implementer task.

## Status
done. Branch `docs/p1-constants-timeout-contracts`, committed, not pushed.

## What changed (and why)
- `pipeline/constants.py` (locked, Architect edit):
  - `SPEECH_WPM` 150 to 144: 167 words in 69.5 s in render run 43873059742.
  - `TIKTOK_WORDS` (156, 225) to (149, 216): 62 s x 144 / 60 = 148.8, rounded inwards to 149; 90 s x 144 / 60 = 216.0, so 216. At 144 wpm a 225-word script would run about 94 s and fail QA.
  - New: `QA_FPS_TOLERANCE` 0.01, `QA_TOOL_TIMEOUT_S` 300, `QA_STDERR_TAIL_LINES` 5, `AUDIO_SAMPLE_RATE_HZ` 48000, `TRUE_PEAK_DBTP` -1.0, `COMPOSE_STDERR_TAIL_LINES` 20, `COMPOSE_TIMEOUT_S` 600. Values unchanged from the private copies, so the literal-pinned tests (`test_compose_exact.py`: "48000", "TP=-1", 20 tail lines) stay valid. The two tail lengths stay separate (20 and 5) because they differ today and only compose's is pinned.
  - `COMPOSE_TIMEOUT_S` 600: the whole render step (voice, alignment, compose, QA) for the 69.6 s video took 125 s in run 43873059742 (step timings via `gh run view`), so 600 s per FFmpeg call leaves room for a 90 s video, well inside render.yml's 45 minute limit.
- `tests/render/test_render_constants.py` (new, locked by `tests/**`, owned by p1-constants-timeout): the timeout is passed on both FFmpeg calls and a `TimeoutExpired` (stderr None or bytes) on either pass becomes a `ComposeError`; each moved constant is patched to an odd value and compose or qa behaviour must follow it.
- `.harness/tasks/phase1/19_constants_timeout.yaml`: one implementer task, `paths_allowed` compose.py and qa.py only.
- Docs: see Docs below.

## Decisions made
- One implementer task, not two. Both changes touch only compose.py and qa.py, the tests share one file, and the moves are mechanical.
- Tests check the moves by behaviour (patch `constants.X`, observe the change), not by asserting private names are gone.
- Existing test files are untouched and stay owned by their tasks; the new tests live in a new file (conftest rule). `locks.yaml` needs no edit: `tests/**` and `pipeline/constants.py` are already locked.
- `RETENTION_WORDS` (70, 112) left as is, and flagged for the owner. At 144 wpm, 25 to 45 s is 60 to 108 words, so 112 words runs about 47 s, over the Retention format's 45 s. `RETENTION_WORDS[1]` is also the word-count switch in `qa.duration_range_for`, so changing it moves which scripts get the 65 s range; that is outside the approved plan. The format is not used by default. The constants.py comment now says it is not derived.

## Tried and abandoned
none

## Known risks
- Heavy `tests/voice/test_kokoro.py` checks voice length against `SPEECH_WPM` with a 40% window; 150 to 144 shifts the expected duration by 4%, well inside. Awaiting CI, not run locally.
- `COMPOSE_TIMEOUT_S` is derived from the whole render step, not from compose alone (no per-call timing in the logs). 600 s has about 4x headroom over the whole step.
- The `RETENTION_WORDS` question above stays open until the owner decides.

## Next step
Owner merges this branch's PR. Then the orchestrator runs p1-constants-timeout as an implementer task (Sonnet), with `LOOM_TASK=p1-constants-timeout`. Then the golden render test to the 65 s sample, then p1-phase-review.

## Docs
- Applied on this branch:
  - spec.md section 4: speech rate, 65 s format word range, voice length check at 144 wpm, Retention note, and two new rows for the render and QA tool numbers.
  - PLAN.md section 4: words column header, 65 s word range and target (about 156), and the tone line (144 wpm).
  - PRD.md: R2.1 to 144 wpm, and a new 2026-11-16 decision entry with the arithmetic and the open Retention question.
  - architecture.md section 7: the SPEECH_WPM/TIKTOK_WORDS weak point replaced by the open `RETENTION_WORDS` one; the compose timeout point notes p1-constants-timeout fixes it.
  - workflow.md: module-order line, criterion-to-test row and a "not started" status row for p1-constants-timeout.
- At p1-constants-timeout close-out: drop the compose timeout weak point from architecture.md section 7, set its workflow.md row to done, add it to status.yaml.
- If the owner re-derives `RETENTION_WORDS`: constants.py, spec.md, PLAN.md section 4 and PRD.md change together, and `tests/test_schema.py::test_acceptance` (the sample must fit `RETENTION_WORDS`) and the switch tests in `tests/render/test_qa.py` and `tests/render/test_qa_exact.py` need re-checking.

## Evidence
Local, Windows, venv with requirements.txt and requirements-dev.txt only:
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues. `python tests/docs_check.py`: passed. `pytest .harness/tests`: 69 passed.
- `pytest` without `LOOM_TASK`: 312 passed, 26 skipped (new file skipped, heavy skipped).
- `pytest` with `LOOM_TASK=p1-constants-timeout`: 313 passed, 11 failed, 14 skipped. The 11 failures are all in `test_render_constants.py`, for the expected reasons: no `timeout` kwarg, `TimeoutExpired` escaping `compose`, and private copies ignoring the patched constants. `test_timeout_is_finite_and_positive` passes (checks only the constant).
- Passable: a throwaway implementation of the YAML notes (compose and qa reading the constants, `TimeoutExpired` mapped to `ComposeError`) made all of `tests/render` pass with `LOOM_TASK` set (129 passed, 7 heavy skipped), existing literal-pinned tests included. Reverted, not committed.
- Existing `TIKTOK_WORDS` users pass with the new range: `tests/test_schema.py::test_default_sample_fits_the_65s_format` (167 words) and `tests/render/test_qa.py` boundary cases.
