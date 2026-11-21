# Handoff: p2c-plan (Architect)

## Goal
Plan what is worth doing before Phase 4 out of the Phase 2b follow-ups (orchestrator.md, twelfth and thirteenth sessions) and the 2026-11-21 mutation report (CI run 44942078820, 401 survivors). Everything else is dropped or deferred, with the reason.

## Status
done (plan and contracts). Branch `docs/p2c-plan`. Waits for the owner to merge it. No owner decision blocks wave 1.

## What changed (and why)
- `.harness/tasks/phase2c/`, two tasks, one wave (they share no path):

| # | Task | Role | Paths | Depends on |
|---|---|---|---|---|
| 00 | p2c-gemini-escapes | implementer | `pipeline/script/gemini.py` | p2b-gemini-shapes |
| 01 | p2c-survivor-tests | test_author | `tests/script/test_survivors.py` | p2b-qa-tests-batch, p2b-qa-tests-factcheck |

- `tests/script/test_gemini_errors.py` (new, locked by `tests/**`, owned by 00). Two paths still raise something other than GeminiError, which the batch does not catch, so the whole weekly run crashes:
  - `_http_message` reads the error body inside the HTTPError handler, so a failed read (IncompleteRead, ConnectionResetError, TimeoutError) escapes raw.
  - `json.loads` raises RecursionError, not ValueError, on deeply nested JSON, in the envelope and in the answer text.
- `pipeline/factcheck/semantic.py`: the `check_script` docstring now says what the code and the locked tests do. Only a SUPPORTED or PARTIAL verdict that names an unlinked fact id becomes UNSUPPORTED. An UNSUPPORTED verdict keeps its own reason. This is contract wording, so the Architect wrote it; no code changed.
- workflow.md: Phase 2c order and status table. CLAUDE.md: the Status "Next" line.

### Mutation triage
I generated each survivor's diff with mutmut 3.8.1's own mutator on main at 8933ed1 (scratch venv under `out/`, not committed) and read every one in the Phase 2 modules.

**Real gaps.** Each one becomes a test in task 01:

| Module | Mutants | What no test checks |
|---|---|---|
| gemini `_parse_answer` | 50 | text split over two model_output steps is joined |
| gemini `_parse_answer` | 54, 55 | non-dict parts, non-text parts carrying "text", and text that is not a str are skipped without a crash |
| gemini `_send_with_one_retry` | 26 | two bare timeouts raise GeminiError (the mutant reaches AssertionError) |
| gemini `_send_with_one_retry` | 31, 34, 35 | URLError with a timeout reason retries once; any other reason does not retry |
| gemini `_http_message` | 9 | a non-UTF-8 error body is still GeminiError |
| batch `run` | 125, 127, 129 | `out_dir` under a missing parent. `out/` does not exist on a fresh runner, so this would break the first live run |
| batch `_check_and_repair` | 26 | the rewrite gets the failure reason |
| batch `_write` | 2 | a writer that always fails is asked exactly SCRIPT_ATTEMPTS times |
| batch `_script_section` | 8, 9 | scenes in the PR body are numbered from 1, the same as the flags |
| validate `_hides_ascii_digit` | 2, 3, 4 | no test reaches it at all. This is the U+32C0 follow-up; the test runs the whole class (80 code points on Python 3.11) |
| validate `_text_problem` | 4, 6, 7, 9, 10 | `x://y` and a `www.` with no TLD are rejected (PRD R12.1) |
| validate `_length_problems` | 7, 21 | narration and tags exactly at their caps pass |
| sources `load_sources` | 3, 5 | slug order: `bloop` before `bloop-2` |

**Equivalent or not worth a test.** No task:
- Log text and arguments: batch `run` 10 to 12, 56 to 59 and 90, `_check_and_repair` 31 to 40, and `_write` 13 to 18.
- Exception message wording: gemini `_parse_answer` 3 to 6, 15 to 21, 30, 49, 63 to 66 and 71 to 79; `_send_with_one_retry` 27 to 30, 32, 33 and 36 to 41; `generate_json` 11 and 13; `_http_message` 14 and 15; `pr_body` 34; and generate's GenerateError texts. Pinning a message tests the wording, not the behaviour. The contract only says the key never appears, and that is tested.
- `encoding="utf-8"` to None or "UTF-8": batch `run` 115, 117, 124, 132, 134 and 139, and `load_sources` 13 and 15. CI is Linux, where the default is UTF-8.
- HTTP header case and `method=None` with a body: gemini `generate_json` 41, 45 and 49 to 59. urllib normalises both.
- `return 1` to `return 2` (batch `run` 13 and 93): any non-zero code fails the workflow step.
- `indent=2` (batch `run` 120 and 121): pydantic reads either.
- Missing `steps` or `content` defaults (`_parse_answer` 24, 26, 43, 45): GeminiError either way.
- `rewritten = None` (`_check_and_repair` 13): falsy, like False.
- `zip(strict=...)` (`_check` 14, 17, 18): semantic's contract already guarantees one verdict per scene.
- The PR body: the cap boundary (`pr_body` 33) has about 10000 characters of margin (p2b-plan evidence). Heading case (`pr_body` 2 to 4, 9, 10, 17, 18), the left-out separator (`pr_body` 20) and the facts list (`_script_section` 13, 19, 21, 25) are cosmetic.
- `AssertionError("unreachable")` (`_send_with_one_retry` 43 to 45), prompt text case (generate `write_script` 3 to 7, `rewrite_line` 6 to 14), argparse `prog` and the log level (batch `main`).
- normalise `_year` 13 and 27: `_group` never returns 100 (`_group(["one", "hundred"], 0)` gives 1).
- validate `_text_problem` 37 and 38: U+007F is not a number character.
- validate `_normalised` 18 and 19: NFKD already turns U+FF61 into U+3002, so the second `.replace` is dead code. It is a one-line cleanup for whoever next edits validate.py, not a task.
- Out of scope: render, voice and `render_one` survivors. That is Phase 1 code reached mostly by heavy tests (pyproject.toml mutmut comment); judge it from coverage.xml.

Expect the count to fall by about 40, not to zero. There is no target number.

## Owner decisions
Neither one blocks wave 1. The defaults are what this plan assumes.
- **O1. Fact-checking title, description, tags and on-screen text.** Default: defer to Phase 4 planning, together with audit F2 (the source credit line).
  - PLAN.md section 5 scopes the exact layer to narration. The owner reads every script before merge.
  - Run as is, the name rule would flag nearly every Title Case title and every source credit ("Source: ... NOAA National Ocean Service" in the sample).
  - A numbers-only check of these fields is the cheap version if you want it now: about one small batch.py and exact.py task, with flags merged per scene so the PR body cap holds.
  - `on_screen_text` is newly noticed here and is in the same unchecked class.
- **O2. CJK numerals and homoglyph number words.** Default: drop.
  - The writer is our own model working from hand-curated sources, and the owner reads every PR.
  - The alternative is a Latin-script allowlist on spoken fields (it would also stop text Kokoro cannot voice). That is a contract change to validate.
- Both are cheapest to judge after the owner's first live run (R13.5): real scripts show whether these fields ever carry a bad number or a foreign script.

## Dropped, with the reason
- **A meaning check on the hook.** The owner settled this in p2b O1. It would change semantic's one-verdict-per-scene contract.
- **Loosening the batch QA tests' `_code` span coupling.** Nothing changes that layout. Task 01 is told to keep its PR-body assertions independent of it.
- **Tests for the equivalent survivors above.**

## Decisions made
- **The survivor tests go in a test_author task, not on this branch.** They pass on current code, need Gate 2 and fit one Opus session. The p2b QA tasks used the same shape.
- **A failed error-body read keeps the status in the message and drops the excerpt.** The retry rule does not change, because `_http_message` only runs on the final raise. A 429 or 5xx with a broken body still gets its one retry.
- **Both `json.loads` calls catch RecursionError.** It is GeminiError with no retry, like any malformed answer.

## Tried and abandoned
- Creating a fresh worktree `.claude/worktrees/docs-p2c-plan`. The session sandbox refused both `git worktree add` and EnterWorktree, so I created `docs/p2c-plan` from origin/main inside the existing `docs-p2b-closeout` worktree. It was clean, and its old branch `docs/owner-gates-1` is already merged.
- Running mutmut locally (no Windows support). Its mutation module does import on Windows, so I used it only to print the mutant diffs.

## Known risks
- The Python versions differ: CI runs 3.12 and I checked on 3.11. Both raise RecursionError for 100000 nested brackets. The digit-hiding set depends on the Unicode tables, which is why task 01 computes it at test time.
- Task 01 may find a real bug. If so it stops and the Architect opens an implementer task, as in p2b.
- The mutant ids shift once 00 changes gemini.py. Task 01 tests behaviour, so this only affects reading the next report.

## Next step
1. Owner: review and merge `docs/p2c-plan`. O1 and O2 can wait for the first live run.
2. Orchestrator: run p2c-gemini-escapes and p2c-survivor-tests in parallel. Security review applies to 00.
3. Close out (status.yaml) and merge, then dispatch `ci.yml` on main for a fresh mutmut report (lessons.md 2026-11-21).
4. **Phase 4 is planned in its own Architect session.** It can start once this branch merges, since it shares no paths with Phase 2c. It owns audit F2 and O1. Before the task graph, it reads the Phase 0 admin status (OAuth consent screen, Meta and TikTok apps) and `docs/threat-model.md` for the new OAuth integrations. Phase 3 stays skipped for the first upload (orchestrator.md, fifth session).

## Docs
- Applied here: workflow.md (Phase 2c order and status), the CLAUDE.md Status "Next" line, and the semantic.py `check_script` docstring.
- Owed at close-out:
  - workflow.md Phase 2c status rows, and status.yaml.
  - architecture.md: none (section 7 does not list these escapes).
  - PRD.md section 7: record O1 and O2 when the owner answers.
- lessons.md: none. No new mistake.

## Evidence
Run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe`, because the system Python's `tests` package shadows the repo's.
- `tests/script/test_gemini_errors.py` with `LOOM_TASK=p2c-gemini-escapes`, on current code: 19 failed, 0 passed. The failures are the raw IncompleteRead and RecursionError.
- With a throwaway fix (try around `error.read()`, RecursionError added to both `json.loads` excepts), that file plus `test_gemini.py`, `test_gemini_shapes.py` and `test_gemini_redirect.py` gave 69 passed. Restored with `git checkout` and not committed.
- Behaviours task 01 relies on, checked on current code: `x://y` and `see www. now` are rejected as URLs; U+32C0, U+3358 and U+32C8 are rejected as non-ASCII numbers. Sorted by full file name, `bloop-2.yaml` comes before `bloop.yaml`, so the stem key matters.
- `pytest` without LOOM_TASK: 1216 passed, 49 skipped (the new file skips).
- `ruff check .`: passed. `mypy --strict pipeline/`: 22 files, no issues. `tests/docs_check.py`: passed. `pytest .harness/tests`: 69 passed.
