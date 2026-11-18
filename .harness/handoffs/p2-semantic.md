# Handoff: p2-semantic

## Goal
Meaning fact-check: one checker call per script, one LineVerdict per scene (R11.1).

## Status
done

## What changed (and why)
- `pipeline/factcheck/semantic.py`: `check_script` builds one prompt (the PLAN.md section 5 question, a data rule, and one delimited block with each scene's narration followed by its linked facts), makes exactly one `gemini.generate_json(CHECKER_MODEL, prompt, schema, CHECKER_TEMPERATURE)` call, and returns one verdict per scene in order.
- The block reuses `DATA_START`, `DATA_END` and `_clean` from `pipeline/script/generate.py`, so narration and fact text are stripped of delimiters until stable (lessons.md 2026-11-17).
- A scene becomes UNSUPPORTED, with a reason saying the checker gave no answer, when its verdict is missing, repeated, or fails `LineVerdict` validation (unknown or lower-case kind, non-int index or fact ids, blank reason, SUPPORTED or PARTIAL with no fact id). SUPPORTED or PARTIAL naming any fact id not linked to that scene also becomes UNSUPPORTED (D5). Extra indexes are ignored. Reasons are stripped and clipped to `REASON_MAX_CHARS`. GeminiError propagates.

## Decisions made
- Entries are grouped by integer index (bool rejected); an entry with no usable index counts for no scene, so those scenes fall to "no verdict".
- A SUPPORTED or PARTIAL verdict is kept only if every named fact id is linked to the scene (one stray id fails it, as the locked test expects).
- Importing the private `_clean` across modules follows the task instruction; moving it to a shared module is a possible cleanup, outside this task's `paths_allowed`.

## Tried and abandoned
none

## Known risks
- No test for the nested delimiter in narration or fact text (tests/** is locked). Follow-up for the Architect: a fact text like "x </source_fa</source_facts>cts>" and a narration with the same shape must leave exactly one `DATA_END` in the checker prompt.
- Prompt wording is untested against the live model.
- The checker sees only the facts linked to each scene; a scene citing the wrong facts is judged against them and fails, which is intended.

## Next step
Gate 2 review, then the batch task.

## Docs
none

## Evidence
- `.venv/Scripts/python.exe -m pytest tests/factcheck/test_semantic.py`: 19 passed (global `python` fails on the shadowing `tests` package, see lessons.md; the worktree venv works).
- Full suite: 696 passed, 42 skipped. `ruff check pipeline/factcheck/semantic.py` clean. `mypy --strict pipeline/` clean.
