# Handoff: p4b-youtube-contracts (test_author)

## Goal
Contract change for the YouTube upload (audit F1 and F4, QA lead's token note, phase review T1): declare paid product placement false on every insert, refuse an access token outside `^[\x21-\x7e]+$` before `::add-mask::`, and reword the credit line.

## Status
partial: every edit is written and committed; no check could run (see ENV_ISSUE.md). Awaiting local checks and the docs/* PR's Linux CI.

## What changed (and why)
- `pipeline/constants.py`: new `YOUTUBE_PAID_PRODUCT_PLACEMENT = False` (F1: since the 2026-11-16 API revision an unset value means "not declared free of paid placement"). `YOUTUBE_CREDIT_LINE` now reads "Sources: Wikipedia (CC BY-SA 4.0) or public records. Narrated with a synthetic voice." (F4, owner 2026-11-22).
- `tests/test_schema_publish.py`: credit-line literal updated in place; pins `YOUTUBE_PAID_PRODUCT_PLACEMENT is False`. Holds as soon as this merges.
- `tests/publish/test_youtube.py`: loosened two assertions so they hold before and after p4b-youtube. `part` must contain snippet and status (subset, not equality); the init body's `snippet` and `status` are compared on their own, not the whole body. Not added to any `tests:` list.
- New `tests/publish/test_youtube_placement.py` (owned by p4b-youtube, skips on main until it is done):
  1. `part` is exactly `["snippet", "status", "paidProductPlacementDetails"]` in order, `uploadType=resumable`.
  2. The whole init body equals the expected dict from literals and constants, with `paidProductPlacementDetails.hasPaidProductPlacement` checked `is False` (dict equality alone would accept 0).
  3. Six bad tokens (embedded newline, one trailing `\n`, space, tab, carriage return, `é`): each raises `UploadError(sent=False)`, exactly one request, no `::add-mask::` on stdout, token not in the message. Each case gives the fake enough answers for a full upload, so today's youtube.py returns a video id and the `pytest.raises` fails (lessons.md 2026-11-15).
  4. `test_acceptance` runs 1 to 3.
- `workflow.md` R15 row: the new file added in plain text.

## Decisions made
- The new file has its own small fixtures (env, mp4, install) instead of importing from test_youtube.py: importing fixtures from a locked test module trips ruff (F401, F811) and couples two task-owned files.
- The token test calls `capsys.readouterr()` first, because `test_acceptance` runs successful uploads (which print a mask line) before it.
- No test for reading the placement flag from constants at call time: not asked for, and the constant is pinned in test_schema_publish.py.

## Tried and abandoned
none

## Known risks
- Nothing has been run (ENV_ISSUE.md). Possible failures are lint (line length is close to 110 in test_youtube.py's snippet assertion, counted at 107) or a mistake only a run would show.
- The plan's F1 caveat stands: the insert page does not list `paidProductPlacementDetails` as settable; R17 is the live check.

## Next step
1. Run: `ruff check .`, `python tests/docs_check.py`, `pytest -q` without `LOOM_TASK` (expect green, the new file skipped), and `LOOM_TASK=p4b-youtube pytest -q tests/publish` (expect only test_youtube_placement.py to fail: 2 init tests, 6 token cases and test_acceptance).
2. Open the docs/* PR; its Linux CI must be green before merge. Then p4b-youtube implements against the new file.

## Docs
- Applied: workflow.md R15 row (new file, plain text).
- Owed at close-out: backtick tests/publish/test_youtube_placement.py in the R15 row once p4b-youtube is done; PRD section 7 (F1, F4 wording) and the rest are in p4b-docs per the plan. lessons.md: none (no mistake found; the blocked commands are an environment issue, recorded in ENV_ISSUE.md).

## Evidence
- Read: task YAML, p4b-plan, youtube.py, youtube_fakes.py, test_youtube.py, test_schema_publish.py, constants.py, lessons.md 2026-11-15, 02_youtube.yaml (owns the new file).
- Commands: `git status --short` (5 files, all inside paths_allowed). pytest, ruff and docs_check could not run: each needed approval in a non-interactive session.
