# p2-validate-urls (Implementer)

## Goal
CSO P2-3: `validate.problems` must reject bare domains and full-width look-alike URLs, while decimals and abbreviations still pass.

## Status
done. Committed on `task/p2-validate-urls`, not pushed.

## What changed (and why)
- `pipeline/script/validate.py` only:
  - New `_normalised`: NFKC, then U+3002 and U+FF61 mapped to ".", because NFKC leaves the ideographic full stops alone.
  - `_text_problem` runs the URL and angle-bracket checks on the normalised text. The control and invisible character check still runs on the raw text, so NFKC cannot hide one.
  - New `_DOMAIN_LIKE` regex: `[a-z0-9-]+\.[a-z]{2,}`, case-insensitive. A TLD needs 2 or more letters, so "3.5", "2.0", "U.S." and "a.m." pass. NFKC turns "…" into "...", but no letters follow the first dot there, so "wait…and" still passes.
  - The `problems()` docstring rule list says what counts as a URL now.
- Messages are unchanged ("<field>: contains a URL").

## Decisions made
- Regex was ASCII-only at first. The automated security review (MEDIUM) flagged that a Cyrillic or CJK domain slips through, so labels now use Unicode word characters (`[\w-]+`) and the TLD uses Unicode letters (`[^\W\d_]{2,}`). Punycode (`xn--`) forms match as well. Checked by hand on "пример.рф", "例え.日本" and `xn--` names; the locked tests have no non-Latin case, so the Architect may want to add one.
- No path part in the regex: the domain alone is enough to reject, so the path needs no pattern.

## Tried and abandoned
none

## Known risks
- False positive: a sentence missing its space after a full stop ("end.Next") reads as a domain and is rejected. The queue scripts pass `tests/test_queue_scripts.py` with the new rule. Seeded source text is not run through `validate`, so I did not check it separately.
- Non-Latin text with a dot directly before 2 or more letters and no space ("слово.Другое") is also rejected as a domain.

## Next step
Gate 2 review and the security specialist review (validate.py is a trigger in `.harness/config.yaml`), then merge.

## Docs
none. The task's `paths_allowed` is only `validate.py`, and its docstring is updated. No other doc states the old two-rule URL check; `architecture.md` and `spec.md` were not changed by this task.

## Evidence
- Venv: `../p2-weekly-workflow/.venv`.
- `LOOM_TASK=p2-validate-urls pytest -q --tb=short tests/script tests/test_queue_scripts.py`: 379 passed, 7 skipped. This includes `test_validate_urls.py` (acceptance and all cases) and `test_validate.py`.
- `LOOM_TASK=p2-validate-urls pytest -q --tb=short` (full suite): 872 passed, 36 skipped.
- `ruff check .`: all checks passed (after the last docstring edit).
- `mypy --strict pipeline/`: no issues in 21 files.
- `python tests/docs_check.py`: passed.
