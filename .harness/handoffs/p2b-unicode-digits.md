# p2b-unicode-digits handoff

## Goal
Phase review N2: `validate.problems` rejects non-ASCII number characters in every spoken and published field, so a wrong number cannot get past the exact fact-check, which reads ASCII 0 to 9 only.

## Status
done

## What changed (and why)
- `pipeline/script/validate.py`: new `_NUMBER_CATEGORIES = {"Nd", "Nl", "No"}`. The raw-text loop in `_text_problem` (the one that checks control characters) now also returns `"<label>: contains a non-ASCII number character (U+XXXX)"` for the first character in those categories that is not ASCII 0 to 9. Added the rule to the `problems` docstring.
- Checked on the raw text, by category, as lessons.md 2026-11-18 asks. NFKC was not used: it folds full-width digits but leaves Arabic-Indic and other decimal-digit scripts alone.
- The writer and every rewrite already go through `validate.problems`, so no other file changes.

## Decisions made
- Put the check in the existing per-character loop after the control check, not a second loop. The task leaves its place free.
- Digit test is `"0" <= char <= "9"`, so ASCII digits pass.

## Tried and abandoned
- `pytest` and `python -m pytest` with the system Python: an installed `tests` package in site-packages shadows the repo's `tests/` (lessons.md 2026-11-15). The task `.venv/Scripts/python.exe -m pytest` works.

## Known risks
- Legitimate text with a fraction or superscript ("½ mile", "10²") is now refused and the script is regenerated or edited. This is the intended owner decision O2.
- Security review runs on this task (validate.py is a trigger).

## Next step
Gate 2 and security review, then merge.

## Docs
- architecture.md section 7 (line 136, Phase 2 weak point): add that Nd, Nl and No characters other than ASCII 0 to 9 (fractions, superscripts, Roman numerals) are refused too, with the "non-ASCII number character" message. Outside my `paths_allowed`, so applied at close-out.
- lessons.md: none; this applies the 2026-11-18 rule, no new mistake.
- PLAN.md, PRD.md, spec.md: none.

## Evidence
- `.venv/Scripts/python.exe -m pytest -q tests/script`: 631 passed, 32 skipped.
- `tests/script/test_validate_digits.py`: 9 passed, including `test_acceptance`.
- `ruff check pipeline/script/validate.py`: clean. `mypy --strict pipeline/script/validate.py`: clean.
- Not run: full suite, `python tests/docs_check.py`, bandit, semgrep (CI Gate 1).
