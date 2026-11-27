# Handoff: p3b-host-placement

## Goal
push_in zooms about the frame centre so the set's ground stays under the host.

## Status
done (light tests only; the render check is the owner's next M1 render).

## What changed (and why)
`pipeline/visuals/sets.py` `set_events`: for push_in the `\move` end point is now
(dx + WIDTH/2 * (1 - S), HEIGHT/2 * (1 - S)), S = PUSH_IN_SCALE, and `\org` is dropped. libass scales a
drawing about its move point, so this keeps the frame centre fixed (plus drift) over the linear
`\t` zoom. Other cameras emit the same `\move(0,0,dx,0)` as before.

## Decisions made
Kept `:g` number formatting for the move end, matching the old output for non-push_in cameras.

## Tried and abandoned
none

## Known risks
Real libass behaviour is only confirmed by a render. Local pytest needs a workaround here: a
`tests` package in site-packages shadows the repo's namespace package, so I ran pytest after
registering the repo `tests` dir as `sys.modules["tests"]`. CI is unaffected.

## Next step
Owner re-renders M1 and checks the host's feet against the sand line during a push_in.

## Docs
none (the `set_events` docstring was already updated with the locked-in design).

## Evidence
`tests/visuals`: 82 passed, 27 skipped (heavy). `ruff check .` clean. `mypy --strict pipeline/` clean.
test_push_in.py all pass, including test_acceptance.
