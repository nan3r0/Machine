# Handoff: p3-ass-kit

## Goal
Implement `pipeline/visuals/ass_kit.py`: pure ASS drawing kit (header, time, colour, dialogue, shape and text events).

## Status
done (no heavy tests in this task).

## What changed (and why)
- `pipeline/visuals/ass_kit.py`: filled in all six functions per the locked docstrings. Text goes through `captions_ass.escape_ass_text` (imported, not copied). Numbers use `:g` so `85.0` prints as `85`.

## Decisions made
- Shape style font and size (Montserrat, 20) are placeholders the drawing never uses; kept inline since no constant exists.
- `ass_colour` accepts lowercase hex and returns uppercase.

## Tried and abandoned
none

## Known risks
- Whether libass puts art origin (0,0) exactly at `\pos` under `\an7` was not checked here; it follows the contract docstring and the spike. The render tasks and heavy tests will show it.

## Next step
Character, cards, charts and router tasks build on this.

## Docs
none

## Evidence
- `ruff check .` clean, `mypy --strict pipeline/` clean.
- `pytest -q` full suite: 1669 passed, 245 skipped (heavy skipped locally); tests/visuals/test_ass_kit.py all pass.
