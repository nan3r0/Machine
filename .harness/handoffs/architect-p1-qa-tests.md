# Handoff: architect-p1-qa-tests

## Goal
Write task `p1-qa-tests` and its locked tests for the Phase 1 QA lead's high-risk gaps. Final owner scope: proposed tests 1 to 13 from `.harness/handoffs/p1-qa-lead.md`, plus 16 (heavy subprocess timeouts) as a small extra. 14 and 15 are skipped.

## Status
done for the Architect's part. Every new test passes on current pipeline code, so no implementer task is needed. Not pushed. p1-qa-tests itself is not done until the three stand-in fixtures are swapped for real captures (Next step).

## What changed (and why)
- `.harness/tasks/phase1/18_qa_tests.yaml`: the task (role test_author). Its notes record the scope, the fixture sources and how CI runs the files.
- New test files, each owned by p1-qa-tests:
  - `tests/render/test_captions_exact.py`: items 1 and 2. Exact escaped strings, and exact Dialogue text showing that only the current word is highlighted.
  - `tests/render/test_compose_exact.py`: items 3, 4, 5 and 13, plus the task acceptance test. Exact render and measure argument lists, two passes with `subprocess.run` faked, the real loudnorm log, and filter escaping checked by a test-side FFmpeg unescaper (hypothesis round trip).
  - `tests/render/test_qa_exact.py`: items 7 and 8. Both duration ranges and their edges, the word-count switch, the gap in both directions, fps, file size and alignment edges, and `measure` and `run_qa` with the tools faked.
  - `tests/voice/test_kokoro_audio.py`: items 6 and 12. KModel and KPipeline arguments, speed, little-endian 16-bit mono output, clipping, a skipped empty chunk, no-audio error; check_wav widths, zero-byte and truncated files, and the peak floor.
  - `tests/voice/test_align_model.py`: items 9 and 10. Model and align arguments, aligner errors, unreadable or zero-rate wavs rejected before the model loads, a whitespace piece skipped, and a hypothesis exact-times property.
  - `tests/test_render_one_files.py`: item 11. Exact captions.ass content, fonts_dir, a nested out dir, and rendering twice into one folder.
  - `tests/render/test_ffmpeg_fixtures.py`: heavy guard and capture. It runs `qa.measure` on a video with two silences (the longer first) and writes the real tool output to `out/frames/ffmpeg-capture/` (the `frames` artifact, uploaded even on failure). It fails if the stand-in fixtures differ in shape.
- `tests/fixtures/ffmpeg/`: `loudnorm_pass1.log` (real), `silencedetect.log`, `ffprobe_video.json`, `ffprobe_voice.json` and a README naming each source.
- Edits to existing files. These files stay owned by their original tasks, so these edits run on main at once:
  - `tests/render/test_captions_ass.py:81`: replaced the circular oracle with a hand unescape (item 1).
  - `tests/test_render_one.py:97` (`timeout=1200`) and `tests/voice/test_kokoro.py:120` (`timeout=600`) (item 16).
- `workflow.md`: module order line, criterion map row and status row for p1-qa-tests.
- `.harness/locks.yaml`: no change. `tests/**` already locks every new file.

## Decisions made
- New tests go in new files. `tests/conftest.py` maps each test file to one task, and the last YAML wins. Listing an existing file under p1-qa-tests would have skipped all of its tests on main until this task is done.
- Expected values are literals or built from `pipeline.constants`, never from module-private names. 48000, -1 dBTP, 20 tail lines and the fps tolerance are written as literals, since those names are moving to constants.py.
- Pass 2 arguments in the compose acceptance test are compared with `build_ffmpeg_args(...)`. That function is pinned exactly by the item 3 tests, so this check only proves that compose wires it up correctly.
- KPipeline and load_model calls are read through `inspect.signature(...).bind`, so passing arguments by position or by keyword are both accepted.

## Tried and abandoned
- Real ffprobe and silencedetect output for the fakes. None exists in any CI log or artifact: run 43903542144 phase-reports holds only reports, the render run logs only compose.log, and QA never logs tool output. FFmpeg must not be installed locally. The three fixtures are therefore stand-ins in FFmpeg's print format. They break the "never hand-write" rule only until the swap: they must be replaced with the guard's real capture before p1-qa-tests goes into done, even if the guard passes. `test_qa_exact.py` reads its expected numbers from the fixtures with its own JSON and regex parsing, so the swap needs no test edits.
- Running mutmut locally is not possible on Windows with the heavy dependencies. Mutants were confirmed by hand instead (Evidence).

## Known risks
- The silencedetect and ffprobe fixtures are stand-ins until the swap. The guard compares only `streams` and `format`, the keys qa reads, because other top-level keys vary with the FFmpeg version.
- New files skip on main and on any `docs/*` branch until p1-qa-tests is in `.harness/status.yaml` done or is LOOM_TASK. A green CI run on this branch proves nothing for them.
- The scope check rejects a `task/p1-qa-tests` branch until this task YAML is on main. Tried locally with a throwaway ref: "no task p1-qa-tests in .harness/tasks/ on origin/main". This commit also holds the task YAML and this handoff, which are outside any task's scope.
- Equivalent mutants left alive: `ZeroDivisionError` changed to `ArithmeticError` in align `_wav_seconds` (it is a subclass), and `>` changed to `>=` at the exact float limits (noted by the QA lead).
- The filter unescaper does not model av_get_token's whitespace trimming. A path ending in a space is not covered; pipeline paths never end in one.

## Next step
Orchestrator:
1. Push this branch (`docs/p1-qa-tests-contracts`) and open the PR. The owner merges it. The new files skip on main.
2. Run task `p1-qa-tests` on a `task/p1-qa-tests` branch. CI sets LOOM_TASK, so all the new tests and the heavy guard run.
3. Download the `frames` artifact and copy `ffmpeg-capture/*` over `tests/fixtures/ffmpeg/` unchanged. Push until CI is green with the real captures.
4. Gate 2, then merge. The owner adds p1-qa-tests to status.yaml done.
5. A later CI reports run (workflow_dispatch) confirms the mutant kill counts.
Architect follow-ups (constants.py, before Phase 2 scripts): set `SPEECH_WPM` from 150 to 144, and `TIKTOK_WORDS` from (156, 225) to about (149, 216). Also move `_AUDIO_RATE_HZ`, `_TRUE_PEAK_DB`, `_STDERR_TAIL_LINES` (compose) and `_FPS_TOLERANCE`, `_TOOL_TIMEOUT_S`, `_STDERR_TAIL_LINES` (qa) into constants.py. The tests here use literals, so they stay valid after that move.

## Docs
- workflow.md: module order line, criterion map row and status row added (this branch).
- lessons.md, entry to add at close-out (from the p1-qa-lead Docs section): "A test that builds its expected value with the code under test cannot catch that code's bugs." Fixed at `tests/render/test_captions_ass.py:81`. Test added: `tests/render/test_captions_exact.py::test_escape_gives_exact_text`.
- architecture.md section 7: the heavy-only paths (compose subprocess, qa measure, Kokoro audio write, align model call) now have fast fake-based tests. Update the weak point at close-out, and note that the ffprobe and silencedetect fakes rely on the heavy fixture guard.
- status.yaml, workflow.md status and CLAUDE.md status at close-out (Scribe).

## Evidence
- `LOOM_TASK=p1-qa-tests pytest -q`: 312 passed, 14 skipped (heavy). Without LOOM_TASK: 232 passed, 94 skipped, so main stays green.
- `ruff check .`: all checks passed. `mypy --strict pipeline/`: no issues in 11 files. `python tests/docs_check.py`: passed.
- Hand mutations, each reverted, with `git status pipeline/` clean afterwards. Every one made a new test fail:
  - captions: `{` and `}` escapes, the ZWSP, `i == current` inverted, `{\r}` dropped.
  - compose: `-shortest`, `:linear=true` and `-nostdin` removed; `is_file` inverted; log truncation dropped; tail length; colon, quote and backslash escapes; the quote wrapping; OSError handling; the empty-output check.
  - kokoro: `<i2` changed to `>i2`, speed ignored, clip removed, width check, EOFError catch, the peak boundary.
  - align: device, language, `continue` changed to `break`, start taken from the last piece.
  - qa: `abs()` dropped, the end-backwards check removed, `+ SLACK` changed to `- SLACK`, `<=` changed to `<` on the minimum file size, `<=` changed to `<` on the word switch, open-silence handling, `max()` on runs, the fps denominator default, the ZeroDivisionError catch.
  - render_one: fonts dir, `mkdir(parents=...)`, captions content.
- Only survivor: `ZeroDivisionError` changed to `ArithmeticError` (equivalent).
- Heavy tests (`test_ffmpeg_fixtures.py` and the two timeout edits) were not run locally. They are awaiting CI.
