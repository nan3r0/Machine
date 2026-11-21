# Handoff: p2b-qa-tests-batch

## Goal
Locked tests for the QA lead's batch gaps, ranks 1 to 4 (phase review N4), in the new file `tests/script/test_batch_qa.py`. Tests only.

## Status
done

## What changed (and why)
- New `tests/script/test_batch_qa.py`, 14 test cases. It imports its helpers from `tests/script/test_batch.py` (`setup`, `run`, `slug`, `writer_answer`, `FakeGemini`, `REWRITE`, `EXHAUSTED`) and does not edit that file.
  - Rank 1: `test_rewrite_error_keeps_the_script_flagged`, parametrized over a GeminiError and a GenerateError (the rewritten narration contains a URL, which `validate.problems` rejects). The script is written with scene 3 unchanged, the call kinds are `[write, check, rewrite]` with no recheck, and the one flag line is `case-01, scene 3` with the first check's reason.
  - Rank 2: there are three exact-count tests. All 7 scripts failing every line spends writer 14 and checker 14, with one rewrite per script on scene 0 and 49 flag lines. One script failing every line rewrites all 7 scenes and then rechecks once. `CHECKER_MAX_CALLS_PER_BATCH` monkeypatched to 8 binds first (checker 8, writer 8, one rewrite, on case-01). A fourth test, `test_retries_spend_the_writer_budget_exactly`, covers writer retries: writer 14, checker 7, no rewrite, and scene 1 of every script flagged.
  - Rank 3 checks the flag content:
    - an exact failure that persists after the rewrite names the tokens the recheck found;
    - a scene failing both layers gets one flag with both reasons, joined with "; ";
    - a long reason is clipped to exactly 120 characters with its whitespace collapsed;
    - an empty or whitespace-only reason becomes "no reason given";
    - index 4 renders as `- case-02, scene 5: ...`.
  - Rank 4: nine unused sources write slugs 1 to 7. Slugs 8 and 9 never reach Gemini, and the body has no "sources exhausted" line. The out_dir already exists before the run, and the run still returns 0.
  - `test_acceptance` runs the 14/14 budget scenario and the GeminiError rewrite scenario, each in its own subfolder.

## Decisions made
- Every count was derived by hand from the `run` docstring's budget rule (each script still to come reserves SCRIPT_ATTEMPTS writer calls and one checker call) and from the constants. The arithmetic is in each test's docstring. All counts match the QA lead's.
- Clip test: the QA lead's input `"x " * 300` collapses and clips to 120 characters that end in a space, and the strip then leaves 119, so it cannot show "exactly 120". The test uses the unit `"abcdef \n\t "` instead. Its 7 characters do not divide 120, so the clip ends on a letter.
- Persisting exact failure: the rewrite carries 1851 and 1852 in place of the original 1850, so the flag can only have come from the recheck. The tokens are compared as a set because PLAN does not fix their order.
- Both layers: the two reasons are compared as a set after splitting on "; ". The order is not pinned because neither PLAN nor the docstring fixes it.
- Mutant confirmation: every targeted id is still a survivor in `out/reports/mutmut.txt` (2026-11-21). Those ids are `_Budget.__init__` 2 and 4, `spare_checks` 1 and 2, `run` 10 to 13 and 56 to 59, `_write` 2, `_check` 1 to 3 and 14 to 37, `_check_and_repair` 8 to 40, `_flag` 5, 11 and 12, and `_flag_line` 3, 5 and 6. This confirms the ids are present, not their diffs: there is no local `mutants/` tree, so `mutmut show` could not run. None of the four ranks was dropped.

## Tried and abandoned
none

## Known risks
- Whether these tests actually kill the targeted mutants is unproven until the next CI reports run. Some survivors in those ranges may be equivalent (for example the log-argument mutants `_check_and_repair` 31 to 40 and `_write` 13 to 21, which the QA lead called equivalent).
- `mypy --strict` on the new file reports one error that sits in the imported `tests/script/test_batch.py:42` (`Sequence[object] + str`). That error predates this task, and Gate 1 runs mypy on `pipeline/` only.
- No new test failed on current code, so no pipeline bug was found.

## Next step
Gate 2 review. After merge, the next CI reports run confirms the kills.

## Docs
- `workflow.md` line 186: set the p2b-qa-tests-batch status to done. Lines 82 to 84 (the criterion to test map for R10.3 to R11.3) could add `tests/script/test_batch_qa.py`. Both are outside `paths_allowed`, so apply them at close-out.

## Evidence
- `pytest -q tests/script/test_batch_qa.py`: 14 passed.
- Full `pytest -q`: 1140 passed, 71 skipped (heavy tests skipped locally).
- `ruff check .`: all checks passed. `python tests/docs_check.py`: passed.
