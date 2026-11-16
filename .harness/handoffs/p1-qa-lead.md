# Handoff: p1-qa-lead

## Goal
Phase 1 phase-end QA review (HARNESS.md section 6b). Judge whether the Phase 1 tests would catch real bugs, using the mutmut and coverage reports from CI run 43903542144 (main at e99e630), and propose the missing tests for a new locked-test task. Read-only.

## Status
done. Read-only review; the proposed tests wait on owner approval.

## What changed (and why)
No files changed. The QA lead is read-only, so the report lives in this handoff (written by the orchestrator from the QA lead's output).

### Report numbers
- coverage.txt: 245 passed, 430 statements, 16 missed, 96% total.
- mutmut.txt holds 558 non-killed entries: 280 survived, 277 no tests, 1 timeout (`kokoro.x_synthesize__mutmut_1`).
- The run summary says 2 timeouts and 438 killed. Only 1 timeout is listed, which puts killed at 439 (997 - 558). One mutant is unaccounted for in the listing; this does not change the findings.

### Survivors by module (280)

| Module | Survived | Real gaps | Heavy-only or cosmetic |
|---|---|---|---|
| render/compose.py | 90 | `build_ffmpeg_args` (39), `_quote_filter_arg` (8), `compose` missing-input check | `compose` 1-43: the fast test leaves at the input check |
| voice/kokoro.py | 76 (+1 timeout) | `_write_speech` speed, byte order, clip and scale; `check_wav` width and EOF path | Error-message strings in `synthesize` and `_download_pinned` 15/16 |
| voice/align.py | 42 | `align_words` model and align arguments; `to_word_timings` exact times | `align_words` 3-37 are otherwise heavy-only |
| render/captions_ass.py | 37 | `escape_ass_text`, `_line_text` highlight, some `_header` style fields | Message strings, Layer and MarginV, `_ass_time` hours |
| render_one.py | 22 | captions content, `fonts_dir`, `mkdir` flags | argparse `prog` (`main` 2-4), qa.json indent, `encoding=` removals (equivalent on Linux CI) |
| render/qa.py | 13 | boundaries and direction in `_duration_failure`, `_alignment_failure`, `evaluate` | none |

### Real gaps by function
- **compose.py:build_ffmpeg_args** (lines 73-91): 39 survivors. The tests check substrings of the joined command (`test_compose.py:86-111`), and no fast test passes `measured`. Unpinned: `-nostdin` and `-y`; `-f lavfi`; `-b:a AUDIO_BITRATE` and `-ar 48000`; `-shortest` (the video must end with the voice); the pass-2 measured options and `:linear=true` (the lessons.md two-pass loudness fix).
- **compose.py:_quote_filter_arg** (lines 39-40): mutants 14, 15, 18, 19, 22, 27, 28, 29. Quote and colon escaping is checked only by the heavy `test_awkward_paths_render`, which asserts duration > 1 s. lessons.md trap 2 names this exact risk.
- **compose.py:compose** (lines 101-103): an inverted `is_file()` check survives. `test_compose.py:76-83` passes because the other input then raises the same ComposeError; the test checks only the exception type, not which input is named.
- **kokoro.py:_write_speech** (lines 97-112): 56 survivors. The fake KPipeline never yields audio, so the only coverage is the heavy acceptance test, which would not catch: `speed` not reaching KPipeline (the owner's VOICE_SPEED 0.9 decision is unpinned); `"<i2"` changed to `">i2"` (byte-swapped audio is still loud and keeps its length); changed clip bounds or `* 32767`; `lang_code` or the voice path changed.
- **kokoro.py:check_wav**: survivors 2, 4, 12, 20, 23, 27, 34-36. No test uses a non-16-bit wav (line 128 `width != 2`), a zero-byte or truncated file (the EOFError path, line 126), or a peak exactly at VOICE_MIN_PEAK (line 133).
- **align.py:align_words** (lines 35-36): heavy-only, but even the heavy tests would pass with `device`, `download_root` or `language="en"` mutated.
- **align.py:to_word_timings**: mutants 5, 7, 33, 37-39. Both tests (`test_align.py:100-103` and the hypothesis test at 106-120) check invariants only, so a change that keeps the times valid but wrong survives.
- **captions_ass.py:escape_ass_text** (line 34): mutants 15, 17, 19. The oracle is circular (`test_captions_ass.py:81`).
- **captions_ass.py:_line_text** (line 71): mutants 2, 3, 4, 12. Nothing checks that the current word, and only that word, gets `{\1c&H0000FFFF&}` and `{\r}`. This is the R4 highlight requirement.
- **captions_ass.py:_header** (lines 50-65): 18 survivors. The tests read only Alignment and the margins. Unpinned: ScriptType, Bold, BorderStyle, Outline, Encoding, the colours, the Events Format line.
- **captions_ass.py:build_ass**: 2-4 are likely messages (cosmetic); 27 is likely the end-time max/min; 31, 34 and 41 are likely Dialogue formatting and the trailing newline (low).
- **render_one.py:render**: 3-11 are `mkdir(parents, exist_ok)`; the tests use a fresh one-level `out` folder, so a nested or reused folder is never tried. 38-47: the fake `build_ass` at `test_render_one.py:47-49` returns a constant and the content of captions.ass is never compared. `fonts_dir` is ignored at `test_render_one.py:146`. 71-80: qa.json indent and encoding (cosmetic).
- **qa.py:_duration_failure** (lines 48-51): mutants 4, 5, 9. No tests at exactly 25.0 or 45.0 s. No test has a video shorter than its voice (narration cut off), so a dropped `abs()` survives; `test_qa.py:93` checks only the longer case.
- **qa.py:_alignment_failure** (lines 63-65): mutants 5, 8, 9, 13, 16, 19, 20. No test has only `end` going backwards (the swapped case at `test_qa.py:118` fails on the word check first). Nothing checks that an end within ALIGNMENT_SLACK_S past the voice passes, so `+ SLACK` changed to `- SLACK` survives.
- **qa.py:evaluate** (lines 92, 94): mutants 32, 37, 38. No fps or file-size boundary tests.

### No-tests mutants (277), all heavy-only
- align `_wav_seconds` (9)
- compose `build_measure_args` (20), `parse_loudnorm_json` (15), `_tail` (3), `_run_ffmpeg` (31)
- qa `_run`, `_probe`, `_fps`, `_longest_silence`, `measure`, `run_qa` (199)

Most are pure or easy to fake and cheap to kill (proposed tests 4, 5, 8 and 9).

### Coverage gaps (coverage.xml, heavy tests included)
These 16 lines are missed by every test:
- `compose.py:59-60`: `parse_loudnorm_json` error path. `compose.py:109`: empty or missing output. `compose.py:122-123`: OSError starting ffmpeg.
- `qa.py:106-107`: tool timeout or OSError. `qa.py:120-121`: unreadable ffprobe JSON. `qa.py:141`: silence still open at the end of the video, a real behaviour never exercised. `qa.py:165`: measure error wrap.
- `align.py:37-38`: aligner exception becomes AlignError. `align.py:72`: whitespace-only piece skipped. Hypothesis never generates one, and `continue` mutated to `break` would give an IndexError instead of an AlignError.
- `kokoro.py:105`: Kokoro yields no audio.
- `render_one.py:69`: `__main__`. It runs in the heavy subprocess, which coverage cannot see. Not a gap.

### Weak or odd tests
No special-casing of test inputs was found in pipeline code. Test-quality notes:
- `tests/render/test_captions_ass.py:81`: circular oracle.
- `tests/render/test_compose.py:64-73`: checks only that the message is non-empty and the log exists, not that the message carries FFmpeg's stderr tail or that the log has content.
- `tests/render/test_compose.py:76-83`: checks the exception type only.
- `tests/render/test_compose.py:100-111`: substring checks on the joined command.
- `tests/voice/test_kokoro.py:164-167`: the digits and unicode test asserts only duration > 1.0.
- `tests/render/test_qa.py:101-102`: the param table adjusts its timings when `voice_duration_s == 20.0`. A test-side adjustment, not special-casing in code, but hard to read; give that case its own timings.
- `tests/render/test_qa.py:109-112`: reasons are checked only for being non-empty.
- Flakiness: the heavy `subprocess.run` calls at `tests/test_render_one.py:97` and `tests/voice/test_kokoro.py:120` have no `timeout=`, so a hang is bounded only by the CI job limit. The heavy tests need network on a cold model cache. `test_qa.py:40`: `anoisesrc` is unseeded, low risk at amplitude 0.3.

### Proposed tests (for the Test Author; not written)

**P1 (high)**
1. `tests/render/test_captions_ass.py`, `escape_ass_text`: exact expected strings, e.g. `"{x}"` gives `\{x\}`, `"a}b{c"` gives `a\}b\{c`, and `"\N"` gives backslash + ZWSP + `N`. Replace the self-oracle at line 81 with literal expected text. Kills escape 15, 17, 19.
2. `test_captions_ass.py`, `_line_text`/`build_ass` highlight: for dialogue i, exactly one word is preceded by an override containing `\1c&H0000FFFF&`, that word is timings[i].word, `{\r}` follows it, and no other word is highlighted. Kills `_line_text` 2, 3, 4, 12.
3. `tests/render/test_compose.py`, `build_ffmpeg_args`: exact list equality against an expected list built from constants, once without `measured` and once with a measured dict. The second pins `:measured_I=...:offset=...:linear=true`, `-shortest`, `-ar 48000`, `-b:a`, `-f lavfi`, `-y` and `-nostdin`. Kills about 39 `build_ffmpeg_args` mutants.
4. `test_compose.py`, `compose` with `compose.subprocess.run` faked (first call returns real captured loudnorm stderr, second writes `out`). Pins: a missing voice and a missing captions file each raise an error naming that file; the log is created, truncated, then appended in order; pass-1 args equal `build_measure_args(voice)` and pass-2 args contain the parsed values; non-zero exit raises ComposeError ending with exactly the last 20 stderr lines; empty output raises ComposeError (line 109); OSError raises ComposeError (lines 122-123). Kills compose 1-43, `_run_ffmpeg` 1-31, `_tail` 1-3 and `build_measure_args`.
5. `test_compose.py`, `parse_loudnorm_json`: a real loudnorm stderr sample maps to the five options; missing JSON or a missing key raises ComposeError (lines 59-60). Kills `parse_loudnorm_json` 1-15.
6. `tests/voice/test_kokoro.py`, `_write_speech` via a fake KPipeline yielding chunks (one with `audio=None`, values ±1.5). Pins: the KModel config and model paths, and `KPipeline(lang_code=VOICE_LANG_CODE)`; the pipeline is called with the voice `.pt` path and `speed=VOICE_SPEED`, and a custom speed passes through; the output is mono, 16-bit, little-endian, at VOICE_SAMPLE_RATE; samples are clipped to ±32767 and the None chunk is skipped; all-None chunks raise VoiceError and leave no file (line 105). Kills `_write_speech` 1-62 and the related `synthesize` survivors.
7. `tests/render/test_qa.py`, boundaries and direction. Pass: duration 25.0 and 45.0 (with matching timings); gap 0.19, fps 30.009; file size exactly MIN and MAX; end at voice + SLACK/2. Fail: 24.9 and 45.1 s; video 39.5 s against a 40.0 s voice; gap 0.21, fps 30.011; only `end` decreasing at one index (same words); end at voice + SLACK + 0.01. Kills `_duration_failure` 4, 5, 9, `_alignment_failure` 5-20 and `evaluate` 32, 37, 38.
8. `test_qa.py`, the parsers with `qa._run` or `qa.subprocess.run` faked, using real captured silencedetect and ffprobe output: `_longest_silence` returns the max of two closed runs, and an open trailing silence counts up to the duration (line 141); `_fps("30000/1001")` is about 29.97 and `_fps("30")` is 30.0; `measure` with `r_frame_rate` "0/0" raises RuntimeError (line 165) and `run_qa` then returns a failed "duration" report; non-JSON ffprobe output raises RuntimeError (lines 120-121); TimeoutExpired or OSError raises RuntimeError (lines 106-107); a non-zero exit gives a message with the stderr tail. Kills most of the 199 qa no-tests mutants.
9. `tests/voice/test_align.py`, `align_words` with a fake `stable_whisper` in `sys.modules`. Pins: `load_model(ALIGN_MODEL_NAME, device="cpu", download_root=str(cache_dir))`; `align(str(audio), " ".join(words), language="en")`; an aligner exception becomes AlignError (lines 37-38); a whitespace-only piece is skipped (line 72); a garbage or zero-rate wav raises AlignError before the model loads. Kills `align_words` 3-37 and `_wav_seconds` 1-9.

**P2 (medium)**
10. `test_align.py`, hypothesis identity property for `to_word_timings`: when the pieces are already valid (sorted, inside [0, duration], start <= end), each word's start equals its first piece's start and its end equals its last piece's end, exactly. Kills `to_word_timings` 5, 7, 33, 37-39.
11. `tests/test_render_one.py`, `render`: the fake `build_ass` returns unicode marker text and captions.ass must equal it exactly; compose receives `fonts_dir == Path(FONTS_DIR)`; rendering into a nested `out/a/b` works; rendering twice into the same folder works. Kills `render` 3-11 and 38-47.
12. `test_kokoro.py`, `check_wav`: 8-bit and 24-bit wavs are rejected (written with `wave` directly, since `write_wav` is 16-bit only); zero-byte and truncated-header files raise VoiceError; a peak just above VOICE_MIN_PEAK passes. Kills `check_wav` 2, 4, 12, 20, 23, 27, 34-36.
13. `test_compose.py`, `_quote_filter_arg`: exact expected output for a POSIX path containing a space, `'`, `:` and `\`, and for the `fontsdir` value. Optionally a hypothesis round-trip with a test-side unescaper for FFmpeg's two escaping levels. Kills `_quote_filter_arg` 14-29.

**P3 (low)**
14. `test_captions_ass.py`, `_header`: parse the Style line by its Format names and pin Fontname, Fontsize, PrimaryColour WHITE, OutlineColour BLACK, Bold 1, BorderStyle 1, Outline 6, Encoding 1. Also pin ScriptType `v4.00+` and the exact Events Format line. Kills most of `_header` 5-29.
15. `test_captions_ass.py`, `_ass_time`: a hypothesis round-trip (parse(`_ass_time(x)`) within 0.005 for 0 <= x <= 3 h) plus the example `_ass_time(3725.456) == "1:02:05.46"`. Kills `_ass_time` 10.
16. Add `timeout=` to the heavy subprocess calls at `tests/test_render_one.py:97` and `tests/voice/test_kokoro.py:120`.

Skip as cosmetic or equivalent: error-message strings, argparse `prog` (`main` 2-4), qa.json indent, and `encoding="utf-8"` removals (equivalent on Linux CI).

## Decisions made
- Code reached only by heavy tests is judged from coverage.xml, not mutmut (lessons.md 2026-11-16). A survivor in a function that a fast test enters and leaves early (missing input, blank text, a fake that raises) is marked heavy-only, and counts as a real gap only if the heavy test also could not catch the change.
- mutmut.txt lists mutant names but not diffs, so the mutation classes above are inferred from the source. The Test Author confirms each with `mutmut show <id>` before relying on it.
- Number normalisation does not exist in Phase 1 (Kokoro speaks digits itself), so no property test is proposed for it.

## Tried and abandoned
none

## Known risks
- Mutant IDs are mapped to mutation classes by inference, not checked. A few "cosmetic" calls could turn out to be real once confirmed.
- Float boundaries: `abs(40.2 - 40.0) > 0.2` and `abs(30.01 - 30) > 0.01` are both True in IEEE floats. Boundary tests for the duration gap and fps must use values just inside and just outside the limit (0.19 and 0.21, 30.009 and 30.011), not the exact limit. At float granularity, `>` versus `>=` on those two checks is effectively an equivalent mutant.
- The proposed fast tests for compose and qa fake `subprocess.run` or `qa._run`. Fakes can drift from real FFmpeg output, so the canned stderr (loudnorm JSON, silencedetect lines) should be copied from a real CI log, not written by hand.
- Mutation testing never covers the heavy-only paths (`_run_ffmpeg`, `measure`, Kokoro's audio write). Until the proposed fakes land, those paths are guarded only by heavy tests, which assert loosely.

## Next step
The owner decides which proposed tests to accept. The Test Author then writes them as a new locked-test task (suggested id `p1-qa-tests`) and rechecks the listed mutant IDs with `mutmut show`. P1 items first.

## Docs
- lessons.md, proposed entry: "A test that builds its expected value with the code under test cannot catch that code's bugs." `tests/render/test_captions_ass.py:81` checks `escape_ass_text(timing.word) in plain`, so the expected text comes from the function under test, and `escape_ass_text` mutants 15, 17 and 19 survived. Rule: assert literal expected values for pure transforms and keep oracles independent of the code under test. Test to add: proposed test 1.
- architecture.md section 7 (weak points): heavy-only code (compose subprocess path, qa measure, Kokoro audio write, align model call) has no mutation coverage; proposed tests 4, 6, 8 and 9 close it with fakes.
- workflow.md and status: mark p1-qa-lead done at close-out.
- Note, not a test item: several numbers live outside `pipeline/constants.py`, against the project rule: `qa.py:17-19` (`_FPS_TOLERANCE`, `_TOOL_TIMEOUT_S`), `compose.py:13-16` (`_AUDIO_RATE_HZ`, `_TRUE_PEAK_DB`) and the style numbers at `captions_ass.py:52` (outline 6 and others). The first two are already on the Architect follow-up list in the orchestrator handoff.

## Evidence
- Read-only: Read and Grep only, nothing run.
- Reports: `out/reports/coverage.txt`, `out/reports/coverage.xml` (hits="0" rows), `out/reports/mutmut.txt` (status greps and line ranges), from CI run 43903542144 at e99e630.
- Source: all of `pipeline/` except `schema.py` and `constants.py` (constants read for boundary values only).
- Tests: test_align, test_kokoro, test_captions_ass, test_compose, test_qa, test_render_one, `tests/wavs.py`.
- Also lessons.md, `.harness/tasks/phase1/11_qa_lead.yaml` and HARNESS.md section 6b.
