# Handoff: p3-cards

## Goal
Data card layouts (steps, timeline, place card) as ASS events built with ass_kit.

## Status
done (no heavy test in this task; skipped heavy tests elsewhere in the suite are CI-only, "awaiting CI" for those)

## What changed (and why)
- `pipeline/visuals/cards.py`: `steps_events`, `timeline_events`, `place_events`. Shared `_rows` builds panel + staggered rows (number or dot, label, value). Place card: pin, three staggered sonar rings (scale and fade via `\t`), place name, optional value. All events use layer ASS_LAYER_CARD or +1, `\pos` inside DATA_PANEL, times inside the window. Labels use CARD_STYLE text_event so long labels wrap within the panel margins.

## Review round 1 fixes
- Labels and values left-aligned (`\an4`) at x=180, right of the badge (x=140); font shrinks so a label fits the 720 px column (no wrap, no overlap).
- Value placed from fixed row offsets around the label, not `y + 0.3*row`.
- Place value moved to `_TOP + 580`.
- Dot, pin and rings use `\an5` so they centre on `\pos` and scale about their centre.
- Regression test needs a locked test file: proposed in `CONTRACT_CHANGE.md`, not added. Stopped there.

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

## Round 3 (Architect, escalation after 2 review rounds)

### CONTRACT_CHANGE ruling
Accepted, extended. The round 1 review asked for a regression test and the test file is locked, so the request was right. The proposed test alone was not enough: it only checked the left edge, which the round 2 code already passed, so it could not catch the round 2 blocker. Added to `tests/visuals/test_cards.py`:
- `test_long_label_fits_between_badge_and_panel_edge` (steps and timeline, labels `"A" * 24` and `"THE MARY CELESTE MYSTERY"`): `\an4`, left edge right of the badge, and `x + fs * len * 0.756 <= DATA_PANEL right`.
- `test_long_place_name_fits_the_panel`: the place name, centred, fits the panel on one line.
0.756 is the measured Pillow advance of "A" in `assets/fonts/Montserrat-Bold.ttf` per unit of font size (caps average 0.735). It is a test constant from the font, not copied from cards.py. The 24-character label guarantee is kept. `CONTRACT_CHANGE.md` deleted.

### What changed
- `pipeline/visuals/cards.py`: `_CHAR_WIDTH` 0.6 to 0.76 (comment says where it comes from); a `_fit(text, size)` helper used for row labels, row values, the place name and the place value; module docstring now says text is shrunk to one line of the 720 px column instead of claiming it wraps. A 24-character label gets fs 39 (about 708 px by Pillow, under 720).

### Decisions made
- Shrink only, no `\N`: two-line labels bring back the row collision from round 1 item 2, and `escape_ass_text` would escape a `\N` anyway.
- Pillow (em-based) over-states the width libass draws, since libass sizes the font to ascent + descent (1.219 em for Montserrat). So the bound is conservative; the cost is that labels over 18 characters shrink a little more than needed.

### Tried and abandoned
- 0.72 as suggested: Pillow puts "A" at 0.756 em, so 24 "A"s at the resulting fs 41 measure 744 px, over 720.

### Known risks
- Labels made mostly of W or M (1.16 and 0.96 em) can still exceed 720 px by the Pillow measure. In libass units they come to about 0.95 and 0.78 of the font size, so a 24-character all-W label could still overflow. A real label is unlikely to look like that.
- scope_check fails: `tests/visuals/test_cards.py` is under `tests/**` in locks.yaml and this task's role is implementer. Widening the task YAML on this branch cannot help, because scope_check reads the YAML and locks from main. The orchestrator must land the test change on main (or merge with the Architect's test commit recorded as the exception). Not worked around.
- Env: a third-party `tests` package in the global site-packages shadows the repo's `tests` namespace package, so plain `pytest` fails to collect `tests.visuals`. Ran pytest through a shim that registers the repo's `tests` folder first (no repo change). CI is not affected.

### Evidence
- New tests against the pre-fix round 2 code: 6 failed, 7 passed (row tests fail on the right edge, place tests on width).
- After the fix: `tests/visuals/test_cards.py` 13 passed; full `LOOM_TASK=p3-cards pytest -q --tb=line`: 1682 passed, 238 skipped.
- `ruff check .`: clean; `mypy --strict pipeline/`: clean.
- `python tests/scope_check.py task/p3-cards main`: failed, `tests/visuals/test_cards.py: locked in .harness/locks.yaml` (expected, see Known risks).

### Docs
none
