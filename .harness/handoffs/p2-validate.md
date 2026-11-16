# Handoff: p2-validate

## Goal
`validate.problems(script)` for the publishable-script checks (CSO P1-3) and the word-count check, called from `render_one` before the voice step (phase review N5).

## Status
done locally. Ruff, `mypy --strict pipeline/` and the full pytest run pass (585 passed, 153 skipped: heavy tests, CI only).

## What changed (and why)
- `pipeline/script/validate.py`: `problems()` returns one line per problem. Length rules (words, narration characters, scenes, title, description, tags) and per-field text rules (no URL, no `<` or `>`, no Cc/Cf/Co/Cs character, newline allowed only in the description). Labels name the field, such as "scene 4 narration" or "tag 2".
- `pipeline/render_one.py`: after Script validation and before the voice step, `validate.problems` runs (called through the module). Any problem raises `ScriptRejected`, which `main` prints one line per problem to stderr and exits 2, with no call to kokoro and no traceback.

## Decisions made
- A small `ScriptRejected` exception in render_one carries the messages, so `render()` keeps its contract (raises, never exits) and `main` stays the one place that sets exit codes.
- Text rules stop at the first problem per field, so one bad character gives one line, not one per character.

## Tried and abandoned
none

## Known risks
- Messages for a field with several bad kinds (a URL and a `<`) show only the first. Fixing one and rerunning shows the next.
- `tests/test_queue_scripts.py` passes, so `queue/approved/sample-65s.json` is fine.

## Next step
Push, CI Gate 1, Gate 2 review.

## Docs
- `workflow.md`: p2-validate done after CI is green.
- `architecture.md` / `spec.md`: render_one now rejects a script with `validate.problems` before the voice step, exit 2 (the CLI exit codes in render_one's docstring already say "invalid script", no change needed there).
- `lessons.md`: the repeat of the escaping mistake. A Python heredoc rewrite turned `"\n"` into a real newline in validate.py; caught by reading the file, repaired with Edit. The existing rule (Edit or Write only, never a heredoc rewrite) covers it, so no new entry.

## Evidence
- `ruff check .`: passed. `mypy --strict pipeline/`: no issues in 21 files.
- `LOOM_TASK=p2-validate pytest -q --cov=pipeline`: 585 passed, 153 skipped; validate.py 98%.
- Task tests: 159 passed (test_validate, test_render_one_validate, test_queue_scripts).
