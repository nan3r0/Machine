# Handoff: p2b-plan (Architect)

## Goal
Turn phase review N1 to N5 (`.harness/handoffs/p2-phase-review.md`) and the QA lead's ranked tests (`p2-qa-lead.md`) into a small task graph with locked tests, before Phase 4. Phase 4 is not touched.

## Status
done (plan and contracts). Branch `docs/p2b-plan`. Waits for the owner to merge it and answer O1 to O3. Wave 1 needs no decision.

## What changed (and why)
- `.harness/tasks/phase2b/`, six tasks:

| # | Task | Role | Item | Paths | Depends on |
|---|---|---|---|---|---|
| 00 | p2b-prompt-data | implementer | N3 | `pipeline/script/prompt_data.py`, `generate.py`, `pipeline/factcheck/semantic.py` | p2-phase-review |
| 01 | p2b-gemini-shapes | implementer | N5 | `pipeline/script/gemini.py` | p2-phase-review |
| 02 | p2b-unicode-digits | implementer | N2 | `pipeline/script/validate.py` | p2-phase-review, O2 |
| 03 | p2b-hook-check | implementer | N1 | `pipeline/script/batch.py` | p2-phase-review, O1 |
| 04 | p2b-qa-tests-batch | test_author | N4, QA ranks 1 to 4 | `tests/script/test_batch_qa.py` | 00, 01, 03, reports re-run |
| 05 | p2b-qa-tests-factcheck | test_author | N4, QA ranks 5 to 7 | `tests/factcheck/test_semantic_qa.py`, `test_exact_qa.py` | 00, 02, reports re-run |

- Order, at most two at once, with no shared path inside a wave: wave 1 is 00 with 01, wave 2 is 02 with 03, then the owner dispatches the CI reports job on main, then wave 3 is 04 with 05.
- New locked tests (`tests/**` already covers them, so `locks.yaml` is unchanged). Each is a new file owned by its task, so main stays green:
  - `tests/script/test_prompt_data.py` (N3). Shared module API, plus nested-delimiter prompts for the writer, the rewrite and the checker. This is the regression test lessons.md 2026-11-17 said the Architect owed. It also covers QA rank 5's "each scene shows only its linked facts".
  - `tests/script/test_gemini_shapes.py` (N5). A `steps` or `content` that is not a list, and a body read failing with IncompleteRead, ConnectionResetError or RemoteDisconnected, must each raise GeminiError with no retry.
  - `tests/script/test_validate_digits.py` (N2). Every Nd, Nl and No code point other than ASCII 0 to 9 (1781 of them) is rejected in each spoken and published field. ASCII digits still pass.
  - `tests/script/test_batch_hook.py` (N1). A made-up number or name in the hook or loop line becomes a flag with no rewrite and no extra call. Only facts the scenes cite back the hook.
- `pipeline/script/prompt_data.py`: a contract stub (delimiters and two documented functions), so the N3 test file can import it.
- `tests/script/test_batch.py::test_main_uses_todays_utc_date`: the clock is now frozen, which fixes the QA lead's UTC-midnight flake. The test asserts the exact Monday and that `main` asks for UTC. It passes on current code.
- workflow.md: Phase 2b module order and status table. CLAUDE.md: Status "Next" line.

## Owner decisions needed
Defaults are what the tests assume. A different answer means the Architect rewrites that test file before its task runs.

- **O1 (N1, contract change). Hook and loop line check.**
  - Default: run the exact layer on the hook and loop line against every fact the script's scenes cite. A failure is flagged with scene None and the reason "hook: ..." or "loop line: ...". It is never rewritten and costs no Gemini call.
  - Not in the default:
    - (a) A meaning check of the hook. That changes semantic's one-verdict-per-scene contract and the batch's `zip(strict=True)`.
    - (b) Rewriting a failing hook. That needs a new `generate` function and budget rules.
    - (c) Checking the title and description. If F2 adds a "Sources: Wikipedia" line, "Wikipedia" would be flagged on every script unless it is exempted.
    - (d) A prompt rule keeping numbers and names out of hooks. That costs hook quality.
- **O2 (N2, contract change). Non-ASCII digits.**
  - Default: `validate.problems` rejects any Nd, Nl or No character other than ASCII 0 to 9 in every field it checks, so ², ½ and Ⅻ are rejected too. The writer is then asked again, or the script is left out.
  - Alternative: fold the digits in `normalise.py`. NFKC alone does not work: it folds full-width digits but not Arabic-Indic or the other digit scripts, so the QA lead's own example would still pass. Folding by `unicodedata.decimal` would also leave TTS and captions with characters they may say or show wrongly.
- **O3 (N4). QA test scope.** Default: QA ranks 1 to 7, split over tasks 04 and 05. Ranks 8 to 11 (generate, the PR body, sources, and the stale gemini and validate items) are out unless you add them. Before wave 3, dispatch the CI reports job on main, because the current survivors are stale.
- Not part of this graph (owner items already open): N6 (accept the unhashed pytest in the validate job, or fold it into P1-4), N7 and audit F1 to F3, R13.5 and R13.6.

## Decisions made
- **N5: a failed body read is not retried.** Only 429, 5xx and timeouts retry, which matches the existing rule for non-timeout URLErrors. The batch leaves that one script out. Not an owner item, because it only changes how a crash surfaces.
- **N2 goes in `validate.py`, not `normalise.py`** (see O2). It rejects by category, as lessons.md 2026-11-18 says.
- **N1 checks against the facts the scenes cite, not the whole source.** This matches the phase review. A source fact no scene cites does not back the hook.
- **N3 shares only the cleaning and wrapping.** Each caller keeps its own line format, so the prompts stay byte for byte the same and the locked prompt tests keep passing. `generate.DATA_START` and `generate.DATA_END` stay importable, because `test_generate.py:18` imports them.
- **N4 tests come after the code tasks.** The budget and flag tests then see the N1 behaviour. They are split in two so each fits one session.
- **The flaky test is fixed here, not in a task.** The edit makes a passing test deterministic and needs no code change.

## Tried and abandoned
- Running pytest with the system Python. An installed `tests` package in site-packages shadows the repo's `tests/` (lessons.md 2026-11-15), and neither PYTHONPATH nor a sys.path insert fixed it. I used the `p2-batch` worktree venv instead.

## Known risks
- `test_prompt_data.py` checks the module and the prompts. It cannot see whether `semantic.py` still imports from `generate`, so the duplicate removal itself rests on the Gate 2 review.
- O2's default rejects characters such as "½" or "²" in descriptions too. The writer retries once, then the script is left out. Watch the first live run for "non-ASCII number" left-out reasons.
- The N1 default flags but does not repair. A hook that often carries an unsupported number would add flags the owner must read in each PR.
- Wave 3 may find real bugs. The QA lead names "twenty ten" as a likely one. Those become new implementer tasks, and the tests are never bent.

## Next step
1. Owner: review and merge `docs/p2b-plan`, and answer O1 to O3.
2. Orchestrator: run p2b-prompt-data and p2b-gemini-shapes in parallel.
3. After O1 and O2: run p2b-unicode-digits and p2b-hook-check in parallel. Security review applies to 01, 02 and 03.
4. Owner: dispatch the reports job on main. Then run p2b-qa-tests-batch and p2b-qa-tests-factcheck.

## Docs
- Applied here: workflow.md (Phase 2b order and status) and the CLAUDE.md Status line.
- Owed at close-out:
  - architecture.md section 7: remove N1 and N2 once their tasks merge; add the QA lead's note on spelled ordinals and lone zero to nine if the owner wants it.
  - PRD.md section 7: record O1 to O3. Also update R9.1 (non-ASCII digits, hook in scope) once 02 and 03 merge.
  - spec.md: add `prompt_data.py` to the Phase 2 layout when 00 merges.
  - workflow.md: add backticks to the wave 3 test paths when their files exist.
- lessons.md: none. No new mistake; the 2026-11-17 entry's owed test now exists in `test_prompt_data.py`.

## Evidence
Run with `../p2-batch/.venv/Scripts/python.exe`, because the system Python's `tests` package shadows the repo's.

**Current code and checks**
- `pytest` without LOOM_TASK: 1126 passed, 70 skipped (the new files skip).
- `ruff check .`: passed.
- `mypy --strict pipeline/`: 22 files, no issues.
- `tests/docs_check.py`: passed.
- `pytest .harness/tests`: 69 passed.

**New tests with LOOM_TASK set, on current code**

| Task | Failed | Passed | The passing ones |
|---|---|---|---|
| p2b-prompt-data | 9 | 5 | guards that already hold |
| p2b-gemini-shapes | 11 | 0 | |
| p2b-unicode-digits | 7 | 2 | category list sanity, ASCII digits pass |
| p2b-hook-check | 5 | 1 | the cited-facts pass case |

**Passable**
- I wrote a throwaway implementation of each of the four (not committed) and ran each new file with the existing tests in the files the task touches:
  - prompt_data: 14 passed;
  - gemini shapes plus `test_gemini.py` and `test_gemini_redirect.py`: 50 passed;
  - unicode digits plus `tests/script/` and `test_queue_scripts.py`: 633 passed;
  - hook check plus `test_batch.py`: 28 passed.
- The originals were restored with `git checkout` after a WIP commit.
- No source yaml, queued script or other test file holds a non-ASCII number character. So where p2b-unicode-digits puts its check in `_text_problem` does not matter.
- The PR body cap holds under N1: a script can now carry two flags with scene None (hook and loop line). `test_batch_hook.py::test_body_with_hook_and_loop_flags_still_fits` checks all 7 scripts at every cap and passes on current code. The margin stays about 10000 characters under `PR_BODY_MAX_CHARS`.
