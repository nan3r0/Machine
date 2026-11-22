# ENV_ISSUE: p4b-youtube-contracts

The session could not run any test or linter. Every Python command needed approval, and this
session is non-interactive, so each was refused:

1. `python -m pytest -q --tb=short tests/publish/test_youtube_placement.py tests/publish/test_youtube.py tests/test_schema_publish.py`
2. `"../p2b-qa-tests-batch/.venv/Scripts/python.exe" -m pytest ...` (also outside the worktree, so `ls` of it was blocked)
3. `pytest -q --tb=short ...`

Git commands run fine. All edits are written and committed on `docs/p4b-youtube-contracts`. What is left
is verification only: `ruff check .`, `python tests/docs_check.py`, `pytest` without `LOOM_TASK`
(expect all green, the new file skipped), and `pytest tests/publish` with `LOOM_TASK=p4b-youtube`
(expect only `tests/publish/test_youtube_placement.py` to fail: 2 init tests and 6 token cases, plus
`test_acceptance`). Then the docs/* PR's Linux CI must be green before merge.

Fix: allow the project venv's python and pytest for task sessions, or run the checks above from the
orchestrator.
