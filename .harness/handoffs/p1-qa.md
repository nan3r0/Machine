# Handoff: p1-qa

## Goal
Automated QA gate: `run_qa` measures a rendered video and returns a `QAReport` (pass/fail plus every failed check with a reason). It never raises on a bad video.

## Status
partial, awaiting CI. The 21 non-heavy tests in `tests/render/test_qa.py` pass. The 3 heavy tests (`test_acceptance`, `test_measure_reads_the_video`, `test_unreadable_video_gives_failed_report`) are skipped locally because ffmpeg is not installed here. A skipped heavy test is not a pass. `measure` has not run against real ffprobe or silencedetect output yet.

## What changed (and why)
- `pipeline/render/qa.py`: `duration_range_for`, `evaluate`, `measure`, `run_qa`, plus private helpers (`_duration_failure`, `_alignment_failure`, `_run`, `_probe`, `_fps`, `_longest_silence`).
- `evaluate` is pure. It builds one QAFailure per failed check and puts every `VideoStats` field in `measured`.
- `measure` runs `ffprobe` (video: duration, width, height, `r_frame_rate` of the first video stream; voice: duration) and `ffmpeg silencedetect` on the video's audio. All calls use argument lists and a 300 s timeout. Any tool failure, bad JSON or missing field becomes a `RuntimeError`, which `run_qa` turns into a failed report with a "duration" failure.
- `silencedetect` runs with `d=MAX_SILENCE_S`, so only silences of at least the limit are reported. A silence still open at end of file counts up to the video duration, in case the ffmpeg version prints no `silence_end` there.

## Decisions made
- fps is compared to `FPS` with a 0.01 tolerance, since ffprobe reports a fraction.
- Alignment checks, in order: timing count equals word count; each word matches in order; start and end never decrease; end no later than voice duration plus `ALIGNMENT_SLACK_S`. The first problem found is reported.
- Duration check reports the range problem first, then the video vs voice mismatch, so each bad video gives one duration failure.
- `_FPS_TOLERANCE`, `_TOOL_TIMEOUT_S` and `_STDERR_TAIL_LINES` are module constants in qa.py because constants.py is locked. The owner decision of 2026-11-15 (alignment sanity replaces the 150 ms speech-rate rule) is implemented as the alignment check.

## Tried and abandoned
none

## Known risks
- `silencedetect` and `ffprobe` output parsing is only proven by the heavy tests in CI.
- The silence check only looks at the video's audio track. A video with no audio stream makes ffmpeg fail, which gives a failed report ("unreadable"), not a silence failure.
- `longest_silence_s` is 0.0 when no silence reaches `MAX_SILENCE_S`, so `measured` does not show shorter silences.

## Next step
Push, let CI run the heavy tests. If green, Gate 2 review.

## Docs
- spec.md / architecture.md: QA measures with ffprobe and `silencedetect` (`d=MAX_SILENCE_S`), so `longest_silence_s` is 0.0 below the limit. Applied at close-out.
- spec.md numbers: fps tolerance 0.01 lives in qa.py (`_FPS_TOLERANCE`); Architect may move it to constants.py.
- workflow.md: p1-qa to done only after CI heavy tests pass.
- lessons.md: none.

## Evidence
- Non-heavy tests via a shim that injects the repo's `tests` package (a `tests` package in site-packages shadows it): 21 passed, 3 skipped (heavy).
- `ruff check pipeline/render/qa.py` clean, `mypy --strict pipeline/` clean.
