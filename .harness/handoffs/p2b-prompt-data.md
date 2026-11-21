# p2b-prompt-data handoff

## Goal
Phase review N3: one shared data-block module for the writer and checker prompts, no behaviour change.

## Status
done

## What changed (and why)
- `pipeline/script/prompt_data.py`: filled in `clean` (repeat removal of both delimiters until stable) and `data_block` (delimiter, each line cleaned, delimiter, joined with newlines). `DATA_START` and `DATA_END` unchanged.
- `pipeline/script/generate.py`: deleted `_clean` and `_data_block`. Imports `clean` and `data_block` from `prompt_data`. `DATA_START` and `DATA_END` are re-exported with `import X as X`, because `tests/script/test_generate.py` imports them from `generate` and ruff would flag them as unused otherwise. The writer and rewrite blocks are built with `data_block(f"{fact.id}:{fact.text}" ...)`; topic, reason and old line go through `clean`. Dropped the now unused `Fact` import.
- `pipeline/factcheck/semantic.py`: no longer imports from `generate`. `_data_block` became `_scene_lines`, which only formats the "Scene i: ..." and "  Fact id: ..." lines; `data_block` cleans and wraps them.
- Prompts are byte for byte what they were: no label ends in a character a delimiter starts with, so cleaning a whole line equals cleaning its untrusted part.

## Decisions made
- Kept the `import X as X` re-export rather than a second copy of the delimiters or an `__all__`. It is the smallest change that keeps the test import working.
- Inlined the fact-line generator at both `generate` call sites, as the task YAML says, instead of a new wrapper helper.

## Tried and abandoned
- A private `_facts_block` wrapper in `generate.py` for the two call sites. Removed to follow the task text.
- Running pytest plainly: an installed `tests` package in site-packages shadows the repo's `tests/` (lessons.md 2026-11-15). Used a one-line `python -c` shim that sets `tests.__path__` to the repo folder. `python -m pytest` alone did not help.

## Known risks
- `test_prompt_data.py` cannot see whether `semantic.py` still imports from `generate`; the duplicate removal rests on Gate 2 review (p2b-plan.md). Checked by grep: no `_clean` or `_data_block` import left from `generate`.

## Next step
Gate 2 review, then merge. Close-out applies the spec.md doc change below.

## Docs
- spec.md: add `pipeline/script/prompt_data.py` to the Phase 2 layout (p2b-plan.md says to do this when 00 merges). Outside my `paths_allowed`, so applied at close-out.
- lessons.md: none. The 2026-11-17 entry's "Test added: none yet" can now point to `tests/script/test_prompt_data.py` (new entry or note at close-out, old entries are not edited).
- architecture.md, PLAN.md, PRD.md: none.

## Evidence
- `ruff check .`: clean. `mypy --strict pipeline/`: clean.
- `tests/script` and `tests/factcheck` (with the `tests` shim): 716 passed, 27 skipped.
- Full `tests/` (shim): 1140 passed, 57 skipped. Skips are heavy or OS-specific tests; no heavy test was needed for this change.
- `tests/script/test_prompt_data.py::test_acceptance` passes.
- Not run: `python tests/docs_check.py`, bandit, semgrep (CI Gate 1).
