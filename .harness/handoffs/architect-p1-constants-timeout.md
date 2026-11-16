# Handoff: architect-p1-constants-timeout

## Goal
Before Phase 2 scripts (owner-approved plan, 2026-11-16): set the speech rate to the measured 144 wpm and re-derive `TIKTOK_WORDS`; move the numbers private to `compose.py` and `qa.py` into `pipeline/constants.py`; give `compose._run_ffmpeg` a timeout. Write the constants change and the locked tests, and plan the implementer task. Round 2 (owner rule, same day): every video runs over a minute, so the unused Retention format is removed.

## Status
done. Branch `docs/p1-constants-timeout-contracts` (PR #50), committed and pushed.

## What changed (and why)
- `pipeline/constants.py` (locked, Architect edit):
  - `SPEECH_WPM` 150 to 144: 167 words in 69.5 s in render run 43873059742.
  - `TIKTOK_WORDS` (156, 225) to (149, 216): 62 s x 144 / 60 = 148.8, rounded inwards to 149; 90 s x 144 / 60 = 216.0, so 216. At 144 wpm a 225-word script would run about 94 s and fail QA.
  - `RETENTION_SECONDS` and `RETENTION_WORDS` removed (round 2). `TIKTOK_SECONDS` (62, 90) is unchanged: 62 s lower bound, 90 s cap.
  - New: `QA_FPS_TOLERANCE` 0.01, `QA_TOOL_TIMEOUT_S` 300, `QA_STDERR_TAIL_LINES` 5, `AUDIO_SAMPLE_RATE_HZ` 48000, `TRUE_PEAK_DBTP` -1.0, `COMPOSE_STDERR_TAIL_LINES` 20, `COMPOSE_TIMEOUT_S` 600. Values unchanged from the private copies, so the literal-pinned tests (`test_compose_exact.py`: "48000", "TP=-1", 20 tail lines) stay valid. The two tail lengths stay separate (20 and 5) because they differ today and only compose's is pinned.
  - `COMPOSE_TIMEOUT_S` 600: the whole render step (voice, alignment, compose, QA) for the 69.6 s video took 125 s in run 43873059742 (step timings via `gh run view`), so 600 s per FFmpeg call leaves room for a 90 s video, well inside render.yml's 45 minute limit.
- `pipeline/render/qa.py` (round 2, Architect edit): `duration_range_for` and the word-count switch are gone; the duration check always uses `TIKTOK_SECONDS`. Done here, not in task 19, because removing the constants would otherwise break main between merges.
- Locked tests updated for round 2:
  - `tests/render/test_qa.py`: the `duration_range_for` test removed; the good stats and heavy acceptance video move from 40 s to 65 s; the too-long case from 50 s to 95 s.
  - `tests/render/test_qa_exact.py`: range edges tested at 10, 149 and 216 words, all against `TIKTOK_SECONDS`; the switch test is replaced by `test_a_video_under_a_minute_fails_whatever_the_word_count` (40 s and 60 s fail, 65 s passes, at 10, 100 and 149 words).
  - `tests/test_schema.py`: the sample is now `sample-65s.json`, checked against `TIKTOK_WORDS` in `test_acceptance`; the duplicate `test_default_sample_fits_the_65s_format` is removed.
  - `tests/test_render_one.py` (heavy golden render): renders `sample-65s.json` and checks `TIKTOK_SECONDS`.
  - `queue/approved/sample-40s.json` deleted, nothing references it.
- `tests/render/test_render_constants.py` (new, locked by `tests/**`, owned by p1-constants-timeout): the timeout is passed on both FFmpeg calls and a `TimeoutExpired` (stderr None or bytes) on either pass becomes a `ComposeError`; each moved constant is patched to an odd value and compose or qa behaviour must follow it.
- `.harness/tasks/phase1/19_constants_timeout.yaml`: one implementer task, `paths_allowed` compose.py and qa.py only (constants.py is locked, so it can never be in `paths_allowed`). The notes say the Retention removal in qa.py is already done and must stay.

## Decisions made
- One implementer task, not two. Both changes touch only compose.py and qa.py, the tests share one file, and the moves are mechanical.
- Tests check the moves by behaviour (patch `constants.X`, observe the change), not by asserting private names are gone.
- New tests live in a new file (conftest rule). The round 2 edits to existing test files stay with their owning tasks, all already done, so they run on main. `locks.yaml` needs no edit: `tests/**` and `pipeline/constants.py` are already locked.
- Retention format removed instead of re-derived (owner rule, round 2). It was unused, and its word-count switch let a short script pass QA against 25 to 45 s.

## Tried and abandoned
- Round 1 kept `RETENTION_WORDS` and flagged it for the owner. Superseded by the owner's over-a-minute rule.

## Known risks
- Heavy tests not run locally, awaiting CI: `tests/voice/test_kokoro.py` (a 4% shift from 150 to 144 wpm, inside its 40% window), the heavy `test_qa.py` acceptance (now a 65 s synthetic video, slower to encode), and the golden render in `tests/test_render_one.py` (now the 65 s sample; the render step took 125 s in run 43873059742, against a 1200 s subprocess timeout).
- `COMPOSE_TIMEOUT_S` is derived from the whole render step, not from compose alone (no per-call timing in the logs). 600 s has about 4x headroom over the whole step.

## Next step
Owner merges PR #50 after CI is green. Then the orchestrator runs p1-constants-timeout as an implementer task (Sonnet), with `LOOM_TASK=p1-constants-timeout`. The golden render already uses the 65 s sample; `GOLDEN_FRAME_TIMES_S` (max 30 s) still covers only the first half, so extending it past 30 s is the remaining golden-render follow-up. Then p1-phase-review.

## Docs
- Applied on this branch:
  - spec.md section 4: speech rate, 65 s format word range (now the only format), voice length check at 144 wpm, Retention row removed, two new rows for the render and QA tool numbers.
  - PLAN.md section 4: every video over a minute (65 s a target), words column header, word range and target (about 156), tone line (144 wpm), Retention row and note removed.
  - PRD.md: R1.1 points at the 65 s sample, R2.1 at 144 wpm, two new 2026-11-16 decision entries (speech rate and timeout; over-a-minute rule and Retention removal), and the two earlier 2026-11-16 entries annotated as superseded.
  - architecture.md section 7: the SPEECH_WPM/TIKTOK_WORDS weak point removed (fixed); the compose timeout point notes p1-constants-timeout fixes it.
  - workflow.md: module-order line, criterion-to-test row and a "not started" status row for p1-constants-timeout.
  - lessons.md: the speech rate entry.
- At p1-constants-timeout close-out: drop the compose timeout weak point from architecture.md section 7, set its workflow.md row to done, add it to status.yaml.
- Task YAMLs 00, 09, 17 and 18 still mention `sample-40s.json` or Retention in their notes; they are records of done tasks and are left as written.

## Evidence
Local, Windows, venv with requirements.txt and requirements-dev.txt only:
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues. `python tests/docs_check.py`: passed. `pytest .harness/tests`: 69 passed.
- `pytest` without `LOOM_TASK`: 311 passed, 26 skipped (new file skipped, heavy skipped).
- `pytest` with `LOOM_TASK=p1-constants-timeout`: 312 passed, 11 failed, 14 skipped. The 11 failures are all in `test_render_constants.py`, for the expected reasons: no `timeout` kwarg, `TimeoutExpired` escaping `compose`, and private copies ignoring the patched constants. `test_timeout_is_finite_and_positive` passes (checks only the constant).
- Passable (round 1): a throwaway implementation of the YAML notes made all of `tests/render` pass with `LOOM_TASK` set, existing literal-pinned tests included. Reverted, not committed.
- Round 2 regression check: the new `test_qa_exact.py` run against main's `qa.py` (temporary worktree, removed) fails 3 cases (`test_a_video_under_a_minute_fails_whatever_the_word_count[10]`, `[100]` and `test_duration_range_edges_pass[10-...]`), because main checks short scripts against 25 to 45 s. All pass on this branch.
