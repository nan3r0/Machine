# Handoff: p2-qa-lead

## Goal
Phase 2 test quality review (HARNESS.md 6b) of `pipeline/factcheck/` and `pipeline/script/`. The focus areas were exact-layer number forms, the flag path and the batch call budgets. Inputs were the CI reports from run 44360049860 in `out/reports/`.

## Status
done (read-only review). The proposed tests below go to the owner, who decides whether they become a locked-test task.

## What changed (and why)
none

## Decisions made
- Mutant diffs were not visible: `mutmut.txt` lists ids only and `mutmut show` could not be run. Survivors are grouped by function and mapped to the behaviour gap. The Test Author confirms the top ids with `mutmut show <id>` before writing tests.
- A survivor is called equivalent only when the function's whole mutable surface is cosmetic: log text, fence length, Decimal precision headroom, `format "f"/"F"`.
- For small domains, exhaustive deterministic loops are recommended over hypothesis. They are complete and cheap, and they kill boundary mutants that random sampling misses.

## Tried and abandoned
none

## Known risks
- **Unicode digits skip the exact layer (CONTRACT_CHANGE candidate, high).** `normalise.py:56` matches `[0-9]` only, so `numbers("７２ seconds")` and Arabic-Indic digits give `[]`. A wrong number written that way passes the exact layer, and TTS may still speak it. Fixing it (NFKC before tokenising) changes the normalise contract, so the owner decides.
- By design, but worth a line in `architecture.md` section 7: spelled ordinals ("fifteenth") and lone zero to nine ("seven seconds") are never checked by the exact layer. Only the meaning layer catches them.
- Stale survivors: the `validate.py` and `gemini.py` survivors predate the hardening PRs. Re-run the reports job before acting on them.
- Flaky (low): `tests/script/test_batch.py:298` `test_main_uses_todays_utc_date` can see 8 days if the run crosses UTC midnight. Fix: freeze `batch.datetime`.

## Next step
Owner reviews the proposed tests. The Test Author writes a locked-test task (tests only, no code change expected except possibly the rank 1 case). Re-run the CI reports job after the hardening PRs first.

### Proposed tests, ranked
Survivor ids are `mutmut.txt` `pipeline.script.batch.x_<fn>__mutmut_N`.

1. **HIGH: `batch.py:150-151` is never run.** Coverage hits=0. Survivors: `_check_and_repair` 8-40.
   - `test_batch.py::test_rewrite_error_keeps_the_script_flagged`, parametrized over GeminiError and an invalid narration (GenerateError) from the rewrite.
   - Assert: the script is written, its kinds are `[write, check, rewrite]` with no recheck, and the flag names that scene with the first reason.
   - Bug missed today: dropping GeminiError from the except tuple would leave the script out, against R11.2.
2. **HIGH: budgets only checked with `<=`.** Survivors: `_Budget.__init__` 2 and 4, `spare_checks` 1-2, `run` 56-59, `_write` 2, `_check` 1-3, `_check_and_repair` 8-26.
   - `test_every_line_failing_spends_the_budget_exactly`: all 7 scripts fail every line; writer calls == 14 and checker calls == 14; exactly one rewrite per script, on scene 0; 49 flags. An off-by-one in the init gives 0 rewrites today and still passes.
   - `test_one_script_rewrites_every_failing_line_then_rechecks_once`: count=1, all fail. Kinds == write, check, 7 x rewrite, check.
   - `test_checker_budget_binds_first`: monkeypatch `constants.CHECKER_MAX_CALLS_PER_BATCH = 8`; assert checker == 8, exactly 1 rewrite, 7 scripts written. With equal 14/14 budgets the `spare_checks` guard can never bind.
   - `test_retries_use_the_writer_budget_so_lines_are_flagged`: add writer == 14 and checker == 7.
3. **MED-HIGH: flag content is not asserted.** Survivors: `_flag` 5/11/12, `_check` 14-37, `_flag_line` 3/5/6.
   - An exact failure that persists after the rewrite: the body has "not in the linked facts: 1850". `test_batch.py:207` only finds "1850", which the old line already contains.
   - A scene failing both layers: one flag, reasons joined with "; ".
   - `GeminiError("x " * 300)`: the flag reason is exactly 120 chars, whitespace collapsed.
   - `GeminiError("")`: reason "no reason given". Without that fallback, Flag NonBlank raises and the whole run crashes.
   - Index 4 renders "case-02, scene 5".
4. **MED: `run` picks at most 7.** Survivors: `run` 10-13. No test has more than 7 unused sources.
   - `test_nine_unused_sources_write_the_first_seven`: slugs 1-7 written, 8 and 9 never called, no "sources exhausted" line.
   - Pre-create out_dir (exist_ok) and assert run still returns 0.
5. **MED: `semantic.py`.** Survivors: `_data_block` 7/10, `check_script` 3/28, `_verdict_for` 3-10/30-35/44-45.
   - Under "Scene i" only its linked facts appear; a `not in` mutant still puts every fact somewhere, so the test at line 63 passes.
   - A fact or narration containing DATA_END gives a prompt with exactly one DATA_END.
   - `{"index": true}` with scene 1 missing: scene 1 is UNSUPPORTED.
   - Reason "  " + "y"*200: verdict stays PARTIAL and reason == "y"*120. Test line 131 only checks `<=`.
   - Exact reasons for no, repeated and malformed verdicts and for "named no fact linked".
6. **MED: the exact layer.** Survivors: `_year` 12-65, `_below_thousand` 12/13/38, `_group` 29, `_phrase` 9/24, `_word_numbers` 21, `_is_name` 3/4.
   - In `tests/factcheck/test_exact.py`, add exhaustive loops: 1..9999 through `words()`; all 90x90 two-group years ("twenty ten" -> 2010 is a likely survivor); every "<10..99> oh <1..9>".
   - Oracle variants: "and" after hundred, a space instead of the hyphen, random case, "a <scale>", and 10**12 "one trillion".
   - Literals: "nine lives" -> [] and "ten men" -> ["10"]; "one hundred one" -> ["101"]; "nineteen five" -> ["19"]; "nineteen oh five forty-two" -> ["1905","42"]; "a thousand and one nights" -> ["1001"]; "nineteen oh" and "give me a" -> no crash; `proper_nouns("McDonald ran it.") == ["mcdonald"]` and "UK police" -> ["uk"]. NASA has 4 capitals and never pins `>= 2`.
7. **MED: hypothesis property for decimals and scales.** `test_exact.py` covers integers only.
   - Generate a Decimal (0-3 places) x suffix (k, M, b, bn, thousand ... trillion) x optional "$".
   - Assert it equals a Fraction-based oracle, and that `unsupported` accepts digits vs words vs comma forms of the same n.
   - Pins the `_digit_number` survivors 25/29/37 (likely equivalent precision headroom).
8. **LOW-MED: `generate.py`.** Survivors: `_checked` 3-5, `write_script` 69-80, `rewrite_line` 6-33.
   - Assert the GenerateError text carries the `validate.problems` line, e.g. "title: contains a URL". It becomes the left-out reason in the PR body.
   - In the rewrite prompt, assert the unlinked facts are absent.
9. **LOW: PR body.** Survivors: `pr_body` 2-34, `_script_section` 8-25.
   - A fact cited by two scenes shows once; headings "## Flags" and "## Left out"; a body exactly at PR_BODY_MAX_CHARS passes.
   - Equivalent: `_code` 6/9, `_fenced` 8/11, `_longest_run` 10 (longer fences stay safe).
10. **LOW: `sources.py`.** `load_sources` 3: "bloop.yaml" and "bloop-2.yaml" order by stem, and a full-name sort differs.
11. **STALE, re-check after the re-run:**
    - gemini: a non-UTF-8 HTTP error body must give GeminiError; excerpt exactly 200 chars; non-model_output steps ignored; text split across two parts joins; full payload and headers asserted.
    - validate: boundaries at exactly the cap pass (TIKTOK_WORDS[0] words, NARRATION_MAX_CHARS, SCENES_MAX).
    - Equivalent: log-argument mutants (`_check_and_repair` 31-40, `_write` 13-21, `main` 25/34), and encoding=None on Linux CI (`run` 104-128, `sources` 13/15).

## Docs
none (an `architecture.md` section 7 note on spelled ordinals and lone zero to nine is proposed under Known risks, the owner's call)

## Evidence
- Read: `out/reports/mutmut.txt` (461 non-killed, about 300 in scope), `coverage.txt` and `coverage.xml` (`batch.py:150,151,245` hits=0), and these files on main: `pipeline/script/batch.py`, `generate.py`, `gemini.py`, `validate.py`, `sources.py`, `pipeline/factcheck/normalise.py`, `exact.py`, `semantic.py`, `tests/script/test_batch.py`, `test_generate.py`, `tests/factcheck/test_exact.py`, `test_semantic.py`.
- The budget counts in item 2 were derived by hand from `_Budget`, with WRITER=CHECKER=14 and SCRIPT_ATTEMPTS=2.
- No commands run; read-only.
