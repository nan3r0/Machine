# Handoff: p3-cards

## Goal
Data card layouts (steps, timeline, place card) as ASS events built with ass_kit.

## Status
done (no heavy test in this task; skipped heavy tests elsewhere in the suite are CI-only, "awaiting CI" for those)

## What changed (and why)
- `pipeline/visuals/cards.py`: `steps_events`, `timeline_events`, `place_events`. Shared `_rows` builds panel + staggered rows (number or dot, label, value). Place card: pin, three staggered sonar rings (scale and fade via `\t`), place name, optional value. All events use layer ASS_LAYER_CARD or +1, `\pos` inside DATA_PANEL, times inside the window. Labels use CARD_STYLE text_event so long labels wrap within the panel margins.

## Decisions made
- Signatures keep the locked stub (items, start, end); no palette parameter, colours come from the CARD_*_RGB constants.
- Panel, dots, line and rings are raw drawings via `ass_kit.dialogue` (shape_event needs art Shape objects, not worth it for primitives).
- Row height capped at 190 px; many items shrink rows to fit the panel.

## Tried and abandoned
none

## Known risks
- Label is centred at panel mid x while the number/dot sits at left+60; a very long first wrapped line could visually overlap the badge. Needs the visual QA pass (no render check done here).
- Row text overlap not checked for more than about 5 items or labels wrapping to 3+ lines.

## Next step
Integrate in scenes.ass assembly; visual QA on a rendered frame.

## Docs
none

## Evidence
- `pytest tests/visuals/test_cards.py`: 7 passed
- full `pytest -q --tb=short` (LOOM_TASK=p3-cards): 1676 passed, 238 skipped
- ruff check: clean; `mypy --strict pipeline/`: clean
- scope_check: see below in the final report
