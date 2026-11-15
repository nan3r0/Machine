# Handoff: p1-align

## Goal
Fill in `pipeline/voice/align.py`: stable-ts forced alignment of the known script text to `voice.wav`, one `WordTiming` per script word.

## Status
partial. Awaiting CI: the three `heavy` tests (`test_acceptance`, `test_unicode_and_punctuation_survive`, `test_unreadable_audio_raises`) need torch and stable-ts, which are not installed locally, so they were not run. All 8 non-heavy tests pass locally.

## What changed (and why)
- `align_words`: rejects blank text first (before any model load), reads the wav duration with the stdlib `wave` module (unreadable audio raises `AlignError` before the model loads), then loads `stable_whisper` inside the function with `ALIGN_MODEL_NAME`, `device="cpu"` and `download_root=cache_dir`, and calls `model.align(audio, text, language="en")`. Pieces come from `result.all_words()`.
- `to_word_timings`: strips whitespace from each piece, checks the joined pieces equal the joined script words (else `AlignError`), maps each character to its piece, and gives each script word the start of its first character's piece and the end of its last character's piece. Piece times are clamped to `[0, audio_duration]` with `end >= start`, then each word is forced non-decreasing in start and end.
- `_wav_seconds`: small helper for the duration and the unreadable-audio error.

## Decisions made
- Text passed to the aligner is `" ".join(text.split())`, so whitespace in the script cannot change the word split.
- A broad `except Exception` wraps only the stable-ts call, because torch, whisper and ffmpeg raise unrelated types. It is re-raised as `AlignError` with the cause chained, so nothing is swallowed.
- Duration is read from the wav header, not from the aligner, so clamping does not depend on aligner output. `voice.wav` is always a wav (Kokoro output).
- No owner message changed a recorded decision.

## Tried and abandoned
none

## Known risks
- The stable-ts API calls (`load_model(..., download_root=)`, `model.align(..., language="en")`, `result.all_words()`) are written from the 2.19.1 API and unverified until CI runs the heavy tests.
- If stable-ts normalises text (for example splits on hyphens or drops symbols), the piece-join check raises `AlignError` rather than guessing. CI will show whether the fixture text triggers it.
- `ruff` and `mypy --strict` pass on the file; Gate 1 `make check` (bandit, semgrep, etc.) was not run locally.

## Next step
Push is for the owner. Run CI; if a heavy test fails on the stable-ts call, fix inside `align_words` only. Then Gate 2 review.

## Docs
none. `ALIGN_MODEL_NAME` and the stable-ts pin were already recorded by earlier tasks; no doc is made false by this diff.

## Evidence
- `python -m pytest tests/voice/test_align.py -q --tb=short -m "not heavy"`: 8 passed, 3 deselected.
- `python -m ruff check pipeline/voice/align.py`: all checks passed.
- `python -m mypy --strict pipeline/voice/align.py`: no issues.
- Installed `requirements-dev.txt` and `requirements.txt` locally to run the tests (no torch, no ffmpeg).
