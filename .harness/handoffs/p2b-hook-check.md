# Handoff: p2b-hook-check

## Goal
Phase review N1: the hook and loop line are spoken but neither fact-check layer saw them. Run the exact check on both against the facts the script's scenes cite.

## Status
done

## What changed (and why)
- `pipeline/script/batch.py`: new `_check_spoken_extras(script, source)`. It runs `exact.unsupported` on `script.hook` and `script.loop_line` against the texts of the union of facts any scene cites. `run` calls it after `_check_and_repair` and adds one Flag per failing field (scene None, "hook: not in the cited facts: ..." or "loop line: not in the cited facts: ...", clipped by `_flag`).
- The `run` docstring step 2 now describes this.
- No rewrite, no extra Gemini call, no entry in the scene-index failures dict, so `rewrite_line` never sees a hook or loop failure.

## Decisions made
- Owner decision O1 default taken as written in the task YAML. No change to a recorded decision.
- The check runs outside `_check_and_repair` so budgets and the semantic one-verdict-per-scene contract are untouched.
- Cited facts are sorted by id for a stable order; the order does not affect the result.

## Tried and abandoned
none

## Known risks
- Title and description stay unchecked (per the task); listed for the owner.
- The hook is checked against the final script, after any rewrites, so a rewrite that drops a fact can newly flag a hook. Intended.

## Next step
Gate 2 review and the security specialist review (batch.py is a trigger).

## Docs
- PRD.md / PLAN.md: if either lists what the exact layer covers, add "hook and loop line, against the union of the facts the scenes cite; flagged, not rewritten".
- architecture.md section 7 (weak points): remove the "hook and loop line unchecked" point if present; keep "title and description unchecked".
- No lessons.md entry: no mistake found.

## Evidence
- `.venv/Scripts/python.exe -m pytest tests/script/test_batch_hook.py tests/script/test_batch.py -q`: 29 passed (system Python shadows `tests`, so the venv was used).
- Full suite: 1133 passed, 64 skipped (heavy tests, awaiting CI).
- `ruff check pipeline/script/batch.py`: clean. `mypy --strict pipeline/`: clean.
