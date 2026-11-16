# Handoff: p2-factcheck-exact

## Goal
Exact fact-check layer: `normalise.numbers`, `proper_nouns`, `plain_words` and `exact.unsupported`, to the stub docstrings, passing `tests/factcheck/test_exact.py`.

## Status
Done. Awaiting Gate 1 in CI; no heavy tests involved.

## What changed (and why)
- `pipeline/factcheck/normalise.py`: replaced the `NotImplementedError` bodies. One token regex finds digit numbers (comma thousands, decimals, ordinal/decade suffix, glued k/m/b/bn, trailing scale word) and letter words. Digit numbers use `Decimal` with a precision sized to the input, so scaled values stay exact. Runs of words joined by spaces or hyphens go to a small parser: groups 0-99, hundreds, scale words, "and" after a scale, "a" before a scale word, and year forms (two groups of 10-99, or a group plus "oh" and a unit). A lone zero-to-nine word is dropped. Proper nouns and plain words share one `_words` helper that cleans words and flags sentence starts.
- `pipeline/factcheck/exact.py`: `unsupported` compares canonical numbers and proper nouns against the facts, numbers first, deduplicated in order of first appearance.
- Docstrings kept as given.

## Decisions made
- Unicode letters count as word characters (`[^\W\d_]`), so non-ASCII text cannot split a word into a fake number word.
- Only the hyphen-minus, U+2010 and U+2011 join number words. An en dash does not ("forty–five" reads as 40).
- A scale word after digits is consumed once ("5 hundred thousand" gives 500, then "thousand" is ignored).
- No owner-message decisions changed.

## Tried and abandoned
none

## Known risks
- "half a million" reads as 1000000 because "a" before a scale word means one, as the contract says. A narration with such a phrase can pass or fail wrongly against a fact written differently.
- Abbreviations ending in a period ("Dr.", "U.S.") open a new sentence, so the next name is not checked. This follows the contract rule.
- Hyphenated names ("Ohio-based") are one word, so they match a fact only if it has the same hyphenated word. Fails safe: flagged, not passed.
- "5m" and "5b" read as millions and billions, per the contract; metres or other units glued to digits with a single k/m/b would misread.

## Next step
Gate 2 review, then the next Phase 2 task that consumes `unsupported`.

## Docs
none. No doc is made false by this diff; `architecture.md` and `workflow.md` status lines can be updated at close-out (task done).

## Evidence
- `pytest tests/factcheck/test_exact.py -q`: 61 passed.
- Full suite `pytest --cov=pipeline`: 386 passed, 14 skipped (heavy, CI only); `normalise.py` and `exact.py` 100% covered.
- `ruff check pipeline/factcheck`: clean. `mypy --strict pipeline/`: clean. `python tests/docs_check.py`: passed.
- Not run locally: bandit, semgrep, gitleaks, pip-audit, actionlint (CI only).
