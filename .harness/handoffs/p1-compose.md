# Handoff: p1-compose

## Goal
Render a solid background, the voice wav and the `.ass` captions to a 1080x1920, 30 fps `final.mp4` with FFmpeg: libx264, AAC, loudness normalised to -14 LUFS.

## Status
partial, awaiting CI (round 1 fix applied: two-pass loudnorm after CI run 43776259185 measured -15.6 LUFS against -14). The 8 non-heavy tests pass; the 3 heavy tests (`test_acceptance`, `test_awkward_paths_render`, `test_corrupt_voice_raises_with_ffmpeg_output`) are skipped locally because ffmpeg is not installed here. A skipped heavy test is not a pass. Nothing has been rendered through FFmpeg or libass yet.

## What changed (and why)
- `pipeline/render/compose.py`: `subtitles_filter_value`, `build_ffmpeg_args`, `compose`, plus private `_quote_filter_arg`.
- The color source is `-f lavfi -i color=...` with the voice as second input and `-shortest`, so the video ends with the voice. `-vf subtitles=filename=...:fontsdir=...`, `-af` loudnorm.
- Round 1: loudnorm is now two-pass. `build_measure_args` runs pass 1 to a null output with `print_format=json`; `parse_loudnorm_json` reads `input_i/tp/lra/thresh` and `target_offset` from the last JSON block of stderr; `build_ffmpeg_args(..., measured)` applies them as `measured_I/TP/LRA/thresh`, `offset` and `linear=true`. Without `measured` it stays single pass. Both calls add `-nostdin`. Pass 1 uses `-loglevel info` because loudnorm prints the JSON at info level.
- `compose` checks both inputs exist, appends both runs' full stderr to `log_path`, and raises `ComposeError` with the last 20 stderr lines on a non-zero exit or a missing or empty output.

## Decisions made
- Path escaping is one helper used for both the captions path and `fontsdir`: `as_posix()`, escape `\`, `:` and `'` for the option parser, then wrap in single quotes so `, ; [ ]` and spaces are safe in the filtergraph. A `'` becomes `\'\''` (option escape, then quote close, literal quote, reopen).
- Single pass missed (-15.6 vs -14): the dynamic mode with the default -2 dBTP limiter pulls integrated loudness down on speech. Two-pass linear fixes that. True peak is set to -1 dBTP as module constant `_TRUE_PEAK_DB` in compose.py (constants.py is locked and has no TP value), to give linear mode headroom; LRA stays at the FFmpeg default.
- `-ar 48000`: loudnorm upsamples to 192 kHz internally, which many players reject. The rate and the 20-line stderr tail are module constants in compose.py, not in constants.py (locked).

## Tried and abandoned
- Single-pass loudnorm (round 0): missed the target on CI, replaced by two-pass.

## Known risks
- Bold on the variable Montserrat through libass is unverified (from the captions handoff). Visual QA on the first real frames decides; if bold is wrong, commit a static Bold font.
- `fontsdir` pointing at `assets/fonts` is only proven by a frame showing Montserrat, not a fallback face. The heavy test extracts frames for visual-qa.
- The quoting layers are checked by the unit tests and by reasoning about FFmpeg's two parsers, but `test_awkward_paths_render` in CI is the real proof.
- `-y` overwrites an existing `out`.

## Next step
Push, let CI run the heavy tests. If green, Gate 2 review and visual QA on the extracted frames. If the loudness test still misses, linear mode likely fell back to dynamic because the peak limit blocks the gain; check out/logs/compose.log and consider a lower TP or an Architect-owned TP constant.

## Docs
- spec.md / architecture.md: compose passes `fontsdir=<fonts_dir>` (caller supplies `FONTS_DIR`) to the subtitles filter, and runs two-pass linear loudnorm (pass 1 measures, pass 2 applies) with TP -1 dBTP and default LRA. Applied at close-out.
- spec.md section on numbers: a true-peak constant (-1 dBTP, `_TRUE_PEAK_DB` in compose.py now) belongs in constants.py once it is unlocked; Architect to move it.
- Tests: no unit tests added, tests/ is locked. Suggested for the Architect: one for `build_measure_args`, one for `parse_loudnorm_json` on a sample JSON, one for the pass-2 argument list with `measured`.
- workflow.md: p1-compose to done only after CI heavy tests pass.
- lessons.md: none yet. Add an entry if CI exposes an escaping bug.

## Evidence
- `python <shim> tests/render/test_compose.py`: 8 passed, 3 skipped (heavy). The shim injects a `tests` module because a `tests` package in site-packages shadows the repo's locally.
- Round 1: same 8 passed, 3 skipped. Parse and pass-2 args checked by hand on a sample loudnorm JSON. Coverage of the subprocess path comes only from the heavy tests.
- `ruff check .` clean, `mypy --strict pipeline/` clean.
