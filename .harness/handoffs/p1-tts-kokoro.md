# Handoff: p1-tts-kokoro

## Goal
Implement `synthesize` and `check_wav` in `pipeline/voice/kokoro.py` against the locked tests in `tests/voice/test_kokoro.py`.

## Status
partial: awaiting CI. The 15 non-heavy tests pass locally. The 3 heavy tests (`test_acceptance`, `test_second_run_uses_cache_offline`, `test_unicode_and_digits_are_spoken`) need torch and the real weights and have not run. Ruff and mypy are not installed locally, so Gate 1 lint and types are also unverified.

## What changed (and why)
- `pipeline/voice/kokoro.py`:
  - `synthesize` checks for blank text and an unpinned voice first, before any import or download. It downloads the three pinned files, checks their sha256, then builds `KModel` and `KPipeline` from the local paths, joins the audio chunks and writes a mono 16-bit wav. Any failure removes `out_path` and is re-raised as `VoiceError`. Nothing retries.
  - `check_wav` reads the wav with `wave` and numpy. It rejects an unreadable file, a wrong format (channels, rate, sample width), zero frames and a peak below `VOICE_MIN_PEAK`, and returns the duration.
  - Two private helpers (`_download_pinned`, `_write_speech`) keep `synthesize` short.
  - `numpy` is imported at module top. It is in `requirements.txt` and is not a heavy library.

## Decisions made
- `synthesize` calls `check_wav` on its own output, so a silent or empty result never survives.
- The `except Exception` in `synthesize` is deliberate. It is the boundary around a third-party model, and it re-raises as `VoiceError`.
- No owner decision was changed.

## Tried and abandoned
none

## Known risks
- The `kokoro` 0.9.4 call shapes (`KModel(config=, model=)`, `KPipeline(lang_code=, model=)`, `pipeline(text, voice=<.pt path>, speed=)` yielding results with a torch `.audio`) are written from the docstring contract and memory of the library, not from a real run. CI heavy tests are the first real check.
- `KPipeline` with `lang_code="a"` may fetch a spaCy model through misaki. If that breaks `test_second_run_uses_cache_offline`, the fix belongs in `requirements-heavy.txt` or the workflow cache. That file is outside this task's `paths_allowed`.
- Local pytest cannot import `tests.wavs`. A stray `tests` package in site-packages shadows the repo's `tests` folder, because the repo folder has no `__init__.py`. I ran the suite by preloading `tests.wavs`. CI is probably unaffected, but this should be checked.

## Next step
Run CI. If the heavy tests fail, fix `kokoro.py` from the logs. If lint or types fail, fix those too.

## Docs
- `CLAUDE.md` Status: add "Done: p1-tts-kokoro" once CI is green and the task is merged.
- `workflow.md` module status: mark the Kokoro voice module done at close-out.
- `lessons.md`: add an entry on the stray site-packages `tests` package shadowing the repo (rule: give the repo's `tests` folder an `__init__.py`, or run pytest from a venv).

## Evidence
- `pytest tests/voice/test_kokoro.py -m "not heavy"` with `tests.wavs` preloaded: 15 passed, 3 deselected.
- `python -m ruff` and `python -m mypy`: "No module named". Not installed; not retried, per the 2-try rule.
