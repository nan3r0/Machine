# p2b-qa-tests-factcheck

## Goal
Locked tests for the QA lead's fact-check gaps, ranks 5 to 7 (phase review N4, owner decision O3).

## Status
done. All new tests pass on current code, so this task found no pipeline bug. "twenty ten" already reads as 2010.

## What changed (and why)
- `tests/factcheck/test_semantic_qa.py` (rank 5), 8 tests:
  - `{"index": true}` with scene 1 missing. The scene comes back UNSUPPORTED with the exact "(no verdict)" reason.
  - The exact reasons for a missing, repeated or malformed verdict, and for SUPPORTED or PARTIAL naming an unlinked fact.
  - An UNSUPPORTED verdict naming an unlinked fact keeps the checker's own reason. D5, as recorded in the p2-contracts handoff, converts only SUPPORTED and PARTIAL.
  - `"  " + "y"*200` stays PARTIAL with reason `"y" * REASON_MAX_CHARS`.

  Helpers are imported from `tests/factcheck/test_semantic.py`, which was not edited.
- `tests/factcheck/test_exact_qa.py` (ranks 6 and 7):
  - Exhaustive loops: 1..9999 through `words()`, each checked four ways (as is, space instead of hyphen, upper case, "hundred and"); every "<1..99> hundred"; all 90 x 90 two-group years; every "<10..99> oh <1..9>". The `words` oracle is imported from `test_exact.py`.
  - Number-word literals from the task and the QA lead list, plus "nineteen oh ten", "nineteen oh dear", "ninety-nine hundred" and the "a <scale>" forms.
  - Proper nouns: "McDonald ran it." and "UK police".
  - A hypothesis property: integer mantissa x 0-3 decimal places x scale suffix (glued, spaced, any case) x optional "$" x optional commas, checked against a Fraction oracle with its own digit formatting (not `Decimal.normalize`).
  - A hypothesis property that `unsupported` accepts the words, digits and comma forms of the same n.
  - `test_acceptance`.

## Decisions made
- Reasons are asserted as exact literals copied from the contract wording. The reason clip uses `constants.REASON_MAX_CHARS` rather than a literal 120, because the project rule keeps numbers in constants.py.
- The UNSUPPORTED-keeps-its-reason test rests on the p2-contracts handoff: "SUPPORTED or PARTIAL naming any fact id not linked to that scene also becomes UNSUPPORTED (D5)".
- Rank 5's linked-facts-per-scene and DATA_END items were not repeated, as the task says.

## Tried and abandoned
- A first mutant-check run included the "timeout" mutants, which loop forever, so it hung. I stopped it and reran with only the "survived" mutants.
- A first semantic mutant-check run reported every mutant as surviving. The cause was my harness: pytest had cached the test module under a bare name, still bound to the real `semantic`. After purging `test_*` modules between runs the results were correct, and a control run with no mutant passed.

## Known risks
- **`semantic.x__scene_lines__mutmut_5` (the `in` to `not in` change) is not killed by `tests/script/test_prompt_data.py::test_checker_shows_each_scene_only_its_linked_facts`.** That test was meant to cover it. I confirmed this in memory: the whole file passes with that mutant active. The test may be vacuous. I did not find the cause because the file is outside paths_allowed. Needs the Architect or the QA lead.
- Equivalent or unspecified mutants, left untested on purpose:
  - `_digit_number` 25: "" and "XXXX" both miss `_SCALES`.
  - `_digit_number` 29: extra precision headroom.
  - `_digit_number` 37: "F" and "f" format a finite Decimal the same way.
  - `_below_thousand` 13, `_year` 13 and `_year` 27: a group never reaches 100.
  - `_phrase` 9: the slice is non-empty only when a next word exists, in both versions.
  - `_phrase` 24: `parsed` is never None after the "one" substitution.
  - `numbers` 3 and 4: `previous_end` is only read after a word has set it.
  - `_below_thousand` 38: differs only on nonsense input such as "one hundred zero thousand", which the spec does not define.
  - `check_script` 3: the prompt paragraph separator. It is not in the task bullets.
- `test_every_number_below_ten_thousand_in_words` runs 40k `numbers()` calls, about 1 s locally.

## Next step
Gate 2 review. Then the Architect looks into the `_scene_lines_5` finding above.

## Docs
- workflow.md, criterion-to-test map: add `tests/factcheck/test_exact_qa.py` next to R9.1, R9.2 and `tests/factcheck/test_semantic_qa.py` next to R11.1. This is outside paths_allowed, so it goes in at close-out.
- No other doc is made false by this change. `tests/**` is already locked in `.harness/locks.yaml`.

## Evidence
- `pytest -q tests/factcheck/test_semantic_qa.py tests/factcheck/test_exact_qa.py`: 35 passed.
- `ruff check tests/factcheck/`: clean after one import-order fix.
- Mutant confirmation against `out/reports/mutmut.txt` (2026-11-21 18:25). I installed mutmut 3.8.1 into a scratch venv in the session scratchpad and wrote nothing to the repo. Each mutant was rebuilt with `mutate_file_contents`, exec'd in memory and selected with `MUTANT_UNDER_TEST`, then the new tests were run against it. Killed:
  - normalise: `_group` 29, `_below_thousand` 12, `_year` 12, 26, 38, 40, 43, 50, 52, 61-65, `_word_numbers` 21, `_is_name` 3 and 4.
  - semantic: `check_script` 29, `_verdict_for` 3-10, 30, 31, 34, 35, 44 and 45.
  - Every other survivor listed in the report for these two modules still survives. Each is in the equivalent or unspecified list above.
- Not run locally: the full suite, mypy and `tests/docs_check.py`. CI covers them.
