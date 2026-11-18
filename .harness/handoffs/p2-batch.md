# Handoff: p2-batch

## Goal
Implement `pipeline/script/batch.py`: the weekly batch (7 scripts, two-layer fact-check, flags, queue files, PR body) behind the locked `tests/script/test_batch.py`.

## Status
done (Gate 1 locally; heavy tests are not involved).

## What changed (and why)
- `pipeline/script/batch.py`: `run`, `pr_body`, `main` and private helpers.
  - `_Budget` counts writer and checker calls as they are made. A rewrite is allowed only while `WRITER_MAX_CALLS_PER_BATCH - writes - SCRIPT_ATTEMPTS * scripts_left >= 1`; the re-check only while `CHECKER_MAX_CALLS_PER_BATCH - checks - scripts_left >= 1` (checked before any rewrite, so a rewrite is never made that cannot be re-checked). Otherwise the line is flagged.
  - `_write` makes `SCRIPT_ATTEMPTS` writer calls at most, retrying only on `GenerateError`.
  - `_check` runs `semantic.check_script` once, then `exact.unsupported` per scene against its linked fact texts. A scene fails on missing exact tokens or a non-SUPPORTED verdict; both reasons are joined.
  - `_check_and_repair` rewrites each failing scene once, then re-checks once if any rewrite landed. A rewrite that raises `GenerateError` or `GeminiError` leaves that scene as is and it is flagged.
  - `GenerateError`/`GeminiError` while writing or checking leaves the script out (Flag with scene None). Zero scripts written returns 1 with no PR body.
  - The body is built before any file is written, so a body over `PR_BODY_MAX_CHARS` raises and leaves no approved files behind.
  - Model text goes in an inline code span (whitespace flattened, ticks longer than any run in it, never at line start) or, for title, description and tags, a fenced block longer than any backtick run. Fact text and urls stay plain.

## Decisions made
- Rewrite indexes come from `enumerate(script.scenes)`, not from `verdict.index`, so they are always in range for `generate.rewrite_line` (which raises IndexError otherwise). `semantic.check_script` returns one verdict per scene, so `zip(..., strict=True)` would fail loudly if that ever broke.
- A `GeminiError` during a rewrite flags the line and keeps the script; during write or check it leaves the script out (spec point 4). Judgement call on the rewrite case: the script was already written and checked, so dropping it would lose work for a line the owner can see flagged.
- The "N of 7" in the exhausted line is the number of scripts written, not picked.
- Flag scene numbers are shown 1-based in the body (`Flag.scene` stays a 0-based index).
- Log lines hold counts and script ids only; error text goes to the PR body (clipped), not the log.

## Tried and abandoned
none

## Known risks
- A re-check judges every line again, so a line that passed the first check can fail the second and is then flagged without a rewrite (its single rewrite is not spent). Rare with a temperature-pinned checker.
- Reserved budget for later scripts is the worst case (two writes each); when their first write succeeds the spare is simply unused, so fewer rewrites happen than the totals allow. This keeps the "all 7 scripts get written first" guarantee.
- Not run against the real Gemini API (tests fake `generate_json`).

## Next step
Gate 2 review, then merge. Phase 2 then needs the weekly workflow wiring this entry point (if a task covers it).

## Docs
- `CLAUDE.md` Status: move p2-batch from "Next" to done in Phase 2.
- `workflow.md`: mark p2-batch done in the status table.
- `architecture.md`: if it describes the batch flow, note the budget reservation rule (rewrites never spend what unwritten scripts need) and that the PR body is built before files are written.
- `lessons.md`: no new entry.

## Evidence
- `pytest tests/script/test_batch.py -q`: 22 passed.
- Full suite `pytest -q --cov=pipeline`: 718 passed, 20 skipped (heavy, CI only); batch.py 98% covered.
- `ruff check .`: clean. `mypy --strict pipeline/`: clean. `python tests/docs_check.py`: passed.
