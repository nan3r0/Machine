# Handoff: p4c-batch-log-reason (implementer)

## Goal
The warning for a left-out script must carry the reason, so an all-fail run is diagnosable.

## Status
done

## What changed (and why)
- `pipeline/script/batch.py` `run`: the Flag built for `left_out` is kept in a variable and its `reason` (already whitespace-collapsed and clipped by `_flag`) is logged: `log.warning("script %s left out: %s", slug, flag.reason)`.

## Decisions made
- Reuse the Flag's reason, no second clipping path. %-style logger args.

## Tried and abandoned
none

## Known risks
GenerateError text can quote clipped model output in public logs. Same text is already in the public PR body; accepted in docs/threat-model.md.

## Next step
Gate 2 and security review (batch.py security trigger).

## Docs
- Done in `pipeline/script/batch.py` (review round 1): module docstring no longer says logs never hold model output; `run` docstring step 4 says the reason is also logged and is the only copy when every script fails.
- No other doc changes needed.

## Evidence
`pytest tests/script -q` 725 passed (temporary empty tests/__init__.py used, removed). ruff clean, mypy --strict clean, docs_check passed.
