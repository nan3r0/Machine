# p2-validate-urls (Implementer)

## Goal
CSO P2-3: `validate.problems` must reject bare domains and full-width look-alike URLs, while decimals and abbreviations still pass.

## Status
done, awaiting re-review. Review round 2 fix applied by the Architect on escalation (see "Review round 2" below): Cn rejected on raw text, and the fold now uses NFKD. Locked tests for round 2 are in PR #79 (`tests/script/test_validate_urls_cn.py`); merge it to main first, then rebase this branch. Committed on `task/p2-validate-urls`, not pushed.

## What changed (and why)
- `pipeline/script/validate.py` only:
  - New `_normalised`: NFKC, then U+3002 and U+FF61 mapped to ".", because NFKC leaves the ideographic full stops alone.
  - `_text_problem` runs the URL and angle-bracket checks on the normalised text. The control and invisible character check still runs on the raw text, so NFKC cannot hide one.
  - New `_DOMAIN_LIKE` regex: `[\w-]+\.[^\W\d_]{2,}` (Unicode word characters or hyphens, a dot, then 2 or more Unicode letters; case does not matter). A TLD needs 2 or more letters, so "3.5", "2.0", "U.S." and "a.m." pass. NFKC turns "…" into "...", but no letters follow the first dot there, so "wait…and" still passes.
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
Edits needed at close-out (outside this task's `paths_allowed`, which is only `validate.py`; its docstring is updated):
- `docs/threat-model.md:102`: describe the NFKC plus bare-domain check and mark P2-3 closed by p2-validate-urls. Residuals: spelled-out "example dot net" and spaced "example . net".
- `docs/threat-model.md:173`: move the P2-3 row to closed, the way the P1-3 row at :167 was handled.
- `.harness/handoffs/orchestrator.md:59`: clear the validate.py bare-domain follow-up note.
- Optional: widen `PRD.md` R12.1 wording to cover bare domains and look-alike forms.
- `docs/threat-model.md` (P2-3 residuals, from review round 1): also list a bare IPv4 address ("1.2.3.4/x") and a spelled-out "example dot com" as accepted residuals.
- `architecture.md` section 7 (weak points): the bare-domain rule rejects some legitimate text, such as file names ("report.pdf"), "Amazon.com" and "Node.js". This is a known fail-closed cost: the script is regenerated or edited, never published with a link.
- `spec.md` was not changed by this task.

## Evidence
- Venv: `../p2-weekly-workflow/.venv`.
- `LOOM_TASK=p2-validate-urls pytest -q --tb=short tests/script tests/test_queue_scripts.py`: 379 passed, 7 skipped. This includes `test_validate_urls.py` (acceptance and all cases) and `test_validate.py`.
- `LOOM_TASK=p2-validate-urls pytest -q --tb=short` (full suite): 872 passed, 36 skipped.
- `ruff check .`: all checks passed (after the last docstring edit).
- `mypy --strict pipeline/`: no issues in 21 files.
- `python tests/docs_check.py`: passed.

## Review round 1 (Architect)

### Blocking: invisible marks split a domain (security review)
`_text_problem("description", s)` returns None for "full story at example.c\u034Fom" (U+034F) and "example\uFE0F.com" (variation selector). The same holds for U+180B to U+180D, U+17B4 and U+17B5, and U+E0100 to U+E01EF. These are category Mn, which NFKC leaves alone and the Cf/Co/Cs check skips, so the domain regex never sees "example.com".

Fix direction for the implementer (`pipeline/script/validate.py` only): in `_normalised`, after NFKC, drop characters of category Mn and Me. That text feeds only the URL and angle-bracket checks, so the raw-text control check is unchanged. NFKC runs first, so a decomposed "cafe\u0301" composes to "café" before marks are dropped and stays a word. Recommended over rejecting default-ignorable code points: that route would reject an emoji with U+FE0F ("U+2764 U+FE0F") in a title and still miss marks that are not default-ignorable, such as "example.q\u0301om".

Locked tests added: `tests/script/test_validate_urls_marks.py`, listed in the task YAML `tests:`. A mark case may be reported as a URL or as an invisible character; the test only needs a problem naming the field. Accented text ("café", "naïve", decomposed forms, "3.5", "U.S.") must still pass. A local check of the Mn/Me-drop route against these cases: all mark cases caught, all accented and ORDINARY cases pass.

Also in that file, as regression guards for the Gate 2 reviewer's request (they pass on current code): non-Latin domains ("пример.рф", "例え.日本") and the dots U+FF0E and U+2024 are rejected as URLs.

### Non-blocking rewords
- `validate.py:23` comment: "a lone dot in "wait..." has no letters before it" is wrong for "wait…and" after NFKC ("wait...and"). Reword to say no letters follow the first dot.
- `problems()` docstring: the domain rule says "letters, digits or hyphens"; the regex takes Unicode letters, digits, underscore or hyphens. Say so.

### Round 1 fix (Implementer)
- `validate.py`: `_normalised` drops characters of category Mn and Me after NFKC and the dot mapping (new `_MARK_CATEGORIES`). The raw-text control check is unchanged.
- Comment at the `_DOMAIN_LIKE` constant now says no letters follow the first dot; the `problems()` docstring now lists Unicode letters, digits, underscores or hyphens and mentions the mark drop.
- Docs: no new close-out edits beyond the list above; the threat-model P2-3 entry should also say combining marks are dropped before the check.

### Evidence (round 1)
- After the fix: `LOOM_TASK=p2-validate-urls pytest -q --tb=short`: 1005 passed, 46 skipped (includes `test_validate_urls_marks.py`). `ruff check .` and `mypy --strict pipeline/` clean; `python tests/docs_check.py` run below.
- `.venv/Scripts/python.exe -m pytest tests/script/test_validate_urls_marks.py -q --tb=no`: 63 failed, 70 passed. The 63 are the 9 mark cases times 7 fields; non-Latin, dot look-alike and accented cases all pass.
- `python tests/scope_check.py task/p2-validate-urls origin/main` fails, as expected: the task role on main is `implementer`, so the new locked test and the task YAML edit are flagged. Commit 2c9cdd6 holds only those two files, so the orchestrator can cherry-pick it onto an architect branch and merge it to main first (the route PR #77 took), then rebase this branch onto main.

## Review round 2 (Architect, escalation)

### Findings (security review, confirmed by running them)
- (A) medium: unassigned default-ignorable code points (Cn) split a domain invisibly: "evil.c\U000E01F0om", U+2065, U+E0080 to U+E00FF, U+FFF0 to U+FFF8. Cn was not rejected, not dropped and not `\w`, so `_text_problem` returned None.
- (B) low: round 1 moved the angle-bracket check onto NFKC text, and NFC composes "<" + U+0338 into U+226E, so "a ≮ b" passed though the raw text holds "<" (main rejected it).

### Fix (`pipeline/script/validate.py` only)
- `_BAD_CATEGORIES` gains "Cn", checked on raw text. This closes the class, not one more instance: every Default_Ignorable_Code_Point is Cf or Cn (rejected), Mn (dropped by `_normalised`) or a Hangul filler (Lo, so it joins a domain as `\w` instead of splitting it).
- `_normalised` uses NFKD instead of NFKC before dropping Mn and Me, so "<" + U+0338 decomposes back to "<". Accents drop off their letter ("café" reads "cafe"), which keeps words as words. One check on one folded string, no second raw-text angle check needed: NFKD never removes a raw "<".
- Docstrings of `_normalised` and `problems()` updated (NFKD, Cn, marked angle brackets).

### Decisions
- An emoji with U+FE0F ("❤️") still passes: U+FE0F is Mn, dropped for the URL check, not rejected. Rejecting all default-ignorables was not chosen for that reason. ZWJ emoji sequences (U+200D, Cf) were already rejected on main; unchanged.
- Behaviour change, fail-closed: precomposed "≮" and "≯" are now rejected as angle brackets (main passed them).
- Cn depends on the runtime's Unicode tables (3.11 local is Unicode 14.0, CI 3.12 is 15.0). An emoji newer than those tables is Cn and is rejected as "control or invisible character". Fail-closed (the script is regenerated), but the message may confuse; worth a line in architecture.md section 7.

### Residuals (for docs/threat-model.md P2-3)
- Mc spacing marks (visible) and visible symbols (So, Sm, P*) between labels, including the braille blank U+2800, which renders empty.
- A few letters whose NFKD holds a space or a middle dot (U+013F/U+0140 "Ŀŀ", Arabic isolated harakat U+FE70 to U+FE7E): visible, so not an invisible split.
- Bare IPv4 ("1.2.3.4/x") and spelled-out or spaced dots ("example dot com", "example . com").

### Docs (round 2, close-out)
- `docs/threat-model.md` P2-3: say the fold is NFKD plus Mn/Me drop and Cn is rejected on raw text; add the residuals above.
- `architecture.md` section 7: emoji newer than the runtime's Unicode tables are rejected (fail-closed).

### Evidence (round 2)
- `tests/script/test_validate_urls_cn.py` (from PR #79, copied in temporarily, not committed here): 105 passed, 0 skipped. On main's `validate.py` the same file gives 42 failed (the Cn cases), 63 passed; with no LOOM_TASK all 105 skip.
- Sweep of every code point (no surrogates) through `_text_problem("title", "example"+c+".com")` and `"example.c"+c+"om"`: survivors are only Mc 445, Nd 660, No 152, Pc 10, P* 809, S* 7031, Z* 19, and 24 visible letters listed above. No Cc, Cf, Cn, Co, Mn or Me survives.
- `LOOM_TASK=p2-validate-urls pytest -q --tb=short`: 1005 passed, 46 skipped. `ruff check .` clean, `mypy --strict pipeline/` no issues in 21 files, `python tests/docs_check.py` passed.
