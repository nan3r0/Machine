# Handoff: p1-qa-tests

## Goal
Add locked tests for the Phase 1 QA lead's high-risk gaps (items 1 to 13 of `p1-qa-lead.md`, plus 16 as a small extra). The tests were written by the Architect (see `architect-p1-qa-tests.md`); this task finishes them: real FFmpeg fixtures and a green run with `LOOM_TASK=p1-qa-tests`.

## Status
done. Fixtures swapped, CI green with the new tests running.

## What changed (and why)
- `tests/fixtures/ffmpeg/silencedetect.log`, `ffprobe_video.json`, `ffprobe_voice.json`: stand-ins replaced by the real tool output the heavy guard captured in CI run 43917100099 (`frames` artifact, `ffmpeg-capture/`), copied unchanged. `loudnorm_pass1.log` was already real (render run 43873059742).
- `tests/fixtures/ffmpeg/README.md`: says all four fixtures are real and names the sources.

## Decisions made
- The heavy guard `tests/render/test_ffmpeg_fixtures.py` stays as a drift check for FFmpeg version changes; it still writes its capture on every run.
- Gate 2 non-blocking test notes (fakes ignoring `capture_output` and `check`, 5-line qa tail not pinned, fps taken from `constants.FPS`, stale guard docstring) are logged, not chased. The tests are locked and the gaps are low value.

## Tried and abandoned
- Hand-written fixtures (the stand-ins): no real silencedetect or ffprobe output existed in any log or artifact. Replaced as above.
- Running mutmut locally: not possible on Windows with the heavy dependencies; mutants were confirmed by hand (Architect handoff Evidence).

## Known risks
- `compose._run_ffmpeg` (compose.py:120) has no `timeout=`; a hung FFmpeg is bounded only by the job limit. `qa._run` has one. Needs its own implementer task with a test (a test now would fail on current code).
- Equivalent mutants left alive: `ZeroDivisionError` to `ArithmeticError` in align, `>` to `>=` at exact float limits.
- A later CI reports run (workflow_dispatch) is needed to confirm mutant kill counts.

## Next step
Owner merges the task PR and adds p1-qa-tests to `status.yaml` done. Then close-out docs and the Architect constants follow-ups below.

## Docs
- lessons.md: add "A test that builds its expected value with the code under test cannot catch that code's bugs." Fixed at `tests/render/test_captions_ass.py:81`; regression test `tests/render/test_captions_exact.py::test_escape_gives_exact_text`.
- architecture.md section 7: heavy-only paths (compose subprocess, qa measure, Kokoro audio write, align model call) now have fast fake-based tests; the ffprobe and silencedetect fakes rely on the real fixtures and the heavy drift guard. Add the missing `timeout=` on `compose._run_ffmpeg` as a weak point.
- workflow.md: status row for p1-qa-tests set to done at close-out. status.yaml and CLAUDE.md status via Scribe.
- constants.py (Architect, before Phase 2 scripts): `SPEECH_WPM` 150 to 144, `TIKTOK_WORDS` (156, 225) to about (149, 216); move the private numbers in compose.py and qa.py into constants.py (tests use literals, so they stay valid).

## Evidence
- CI run 43917100099: heavy guard failed on purpose and saved the real capture.
- CI run 43918370324 (`task/p1-qa-tests`, `LOOM_TASK` set from the branch): check success.
- Local with `LOOM_TASK=p1-qa-tests`: 312 passed, 14 skipped (heavy).
- Gate 2: one low blocker (this handoff missing), now resolved; the rest non-blocking.
