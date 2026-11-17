# Handoff: p2-generate

## Goal
Pick unused sources and write one valid Script from a source with one Gemini call (R10).

## Status
done

## What changed (and why)
- `pipeline/script/sources.py`: `load_sources` reads `sources/*.yaml` into SourceFile objects keyed by stem, in stem order, and raises ValueError naming the bad file. `unused_sources` returns the sources none of whose fact ids appear in any `queue/**/*.json` script (the queue is the ledger, decision D3).
- `pipeline/script/generate.py`: `write_script` builds the prompt from module constants (tone, 65 s format with `TARGET_WORDS` and `TIKTOK_WORDS`, content rules, data rule) plus a single delimited facts block, makes exactly one `gemini.generate_json` call, fills id, topic, platforms, publish_after and each scene's visual itself, and validates with Script, `validate.problems` and a fact-id check. `rewrite_line` rewrites one narration with the failure reason, one call. Both raise GenerateError on any problem; GeminiError propagates.

## Decisions made
- Delimiter text inside a fact is removed before it goes into the block, so a fact cannot close it early.
- The data rule describes the block ("the delimited block below") and does not name the tags, because the prompt must hold exactly one `DATA_START` and one `DATA_END`.
- Fact-id check runs after Script validation: each scene cites at least one id, all ids of the source.

## Tried and abandoned
- Naming the tags in the data rule: put each delimiter in the prompt twice and failed the tests.

## Known risks
- Fact text containing a newline spans several lines in the block; it cannot forge a delimiter, but "each on its own line" then holds per fact, not per physical line.
- A queue file that is not a valid Script makes `unused_sources` raise a pydantic ValidationError rather than skip it (a bad ledger should be loud).
- Prompt wording is untested against the live model.

## Next step
Gate 2 review, then the batch task (owns the retry and counts every writer call).

## Docs
none

## Evidence
- `tests/script`: 207 passed, 22 skipped (heavy/other), run with the repo-first `tests` path shim (installed `tests` package shadows the repo's, see lessons.md).
- `tests/script/test_generate.py`: 22 passed incl. `test_acceptance`.
- `ruff check pipeline tests/script`: clean. `mypy --strict pipeline/`: clean.
