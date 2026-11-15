# Handoff: p1-compose

## Goal
Render a solid background, the voice wav and the `.ass` captions to a 1080x1920, 30 fps `final.mp4` with FFmpeg: libx264, AAC, loudness normalised to -14 LUFS.

## Status
partial, awaiting CI. The 8 non-heavy tests pass; the 3 heavy tests (`test_acceptance`, `test_awkward_paths_render`, `test_corrupt_voice_raises_with_ffmpeg_output`) are skipped locally because ffmpeg is not installed here. A skipped heavy test is not a pass. Nothing has been rendered through FFmpeg or libass yet.

## What changed (and why)
- `pipeline/render/compose.py`: `subtitles_filter_value`, `build_ffmpeg_args`, `compose`, plus private `_quote_filter_arg`.
- The color source is `-f lavfi -i color=...` with the voice as second input and `-shortest`, so the video ends with the voice. `-vf subtitles=filename=...:fontsdir=...`, `-af loudnorm=I=-14`.
- `compose` checks both inputs exist, writes FFmpeg's full stderr to `log_path`, and raises `ComposeError` with the last 20 stderr lines on a non-zero exit or a missing or empty output.

## Decisions made
- Path escaping is one helper used for both the captions path and `fontsdir`: `as_posix()`, escape `\`, `:` and `'` for the option parser, then wrap in single quotes so `, ; [ ]` and spaces are safe in the filtergraph. A `'` becomes `\'\''` (option escape, then quote close, literal quote, reopen).
- Single-pass `loudnorm=I=-14` with FFmpeg defaults for true peak and LRA, since constants.py has no values for them and is locked. Single pass can miss by a fraction of a LU; the test tolerance is 1 LU. If CI shows a miss, a two-pass or a TP/LRA constant needs an Architect change.
- `-ar 48000`: loudnorm upsamples to 192 kHz internally, which many players reject. The rate and the 20-line stderr tail are module constants in compose.py, not in constants.py (locked).

## Tried and abandoned
- none

## Known risks
- Bold on the variable Montserrat through libass is unverified (from the captions handoff). Visual QA on the first real frames decides; if bold is wrong, commit a static Bold font.
- `fontsdir` pointing at `assets/fonts` is only proven by a frame showing Montserrat, not a fallback face. The heavy test extracts frames for visual-qa.
- The quoting layers are checked by the unit tests and by reasoning about FFmpeg's two parsers, but `test_awkward_paths_render` in CI is the real proof.
- `-y` overwrites an existing `out`.

## Next step
Push, let CI run the heavy tests. If green, Gate 2 review and visual QA on the extracted frames. If the loudness test misses, see Decisions.

## Docs
- spec.md / architecture.md: compose passes `fontsdir=<fonts_dir>` (caller supplies `FONTS_DIR`) to the subtitles filter, and single-pass loudnorm with default TP/LRA. Applied at close-out.
- workflow.md: p1-compose to done only after CI heavy tests pass.
- lessons.md: none yet. Add an entry if CI exposes an escaping bug.

## Evidence
- `python <shim> tests/render/test_compose.py`: 8 passed, 3 skipped (heavy). The shim injects a `tests` module because a `tests` package in site-packages shadows the repo's locally.
- Coverage of compose.py: 62% locally; lines 71-83 (the subprocess path) are exercised only by the heavy tests.
- `ruff check .` clean, `mypy --strict pipeline/` clean.
