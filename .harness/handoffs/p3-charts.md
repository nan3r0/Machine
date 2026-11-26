# Handoff: p3-charts

## Goal
Chart layouts as ASS events: a count-up number and growing bars.

## Status
done (no heavy test in this task)

## What changed (and why)
- `pipeline/visuals/charts.py`: `plain_number`, `counter_frames`, `bar_lengths`, `counter_events`, `bars_events`.
- Counter: panel, COUNTER_STEPS frames COUNTER_STEP_S apart (last holds to `end`; step shrinks if the window is shorter), label below. A non-number value is one frame that pops in. Size is fitted from the final value so digits do not change size mid count.
- Bars: 2 to VISUAL_ITEMS_MAX items, one row each: label, bar (grows with `\fscx`, one after another), exact value string right of the bar end. The longest bar is 484 px, so the value column (240 px) plus gap stays inside the panel's 40 px margins. Zero or equal values: `bar_lengths` returns 0.0 for an all-zero list, no division.
- Reuses `_panel` and `_drawing` from cards.py (private names, same package) instead of copying them.

## Decisions made
- Signatures keep the locked stub. Own `_fit(text, size, width)` (guards empty text) with the 0.76 em capital width from p3-cards.
- Count-up is linear; `counter_frames` ends exactly on `value` (frame 30 is the string itself).
- `bars_events` raises ValueError outside 2 to VISUAL_ITEMS_MAX items.

## Tried and abandoned
none

## Known risks
- Drawings use `\an7` with `\fscx1` to `\fscx100`: not checked in a libass render that the bar grows from its left edge (same unchecked-libass class as the negative-x note in p3-sets-art). Needs visual QA.
- Bar-end value text is shrunk to the 240 px column, so a long value (about 12+ characters) gets a small font.
- Label font shrinks for long labels; an all-W label could still overflow slightly (see p3-cards risks).

## Next step
Integrate in scene assembly; visual QA on a rendered frame.

## Docs
none

## Evidence
- `python -m pytest tests/visuals/test_charts.py`: 24 passed (plain venv; no tests-package shadow here).
- full `LOOM_TASK=p3-charts pytest -q --tb=short`: 1693 passed, 227 skipped.
- `ruff check .` clean; `mypy --strict pipeline/` clean; `tests/scope_check.py task/p3-charts origin/main`: passed.
