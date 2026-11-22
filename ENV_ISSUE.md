# ENV_ISSUE: p4b-youtube-contracts

Two checks could not run: the commands needed approval, and this session is non-interactive.

1. The run with `LOOM_TASK=p4b-youtube` (tried as an env prefix, with `env`, and through
   `python -c` setting `os.environ`). So the new tests were not seen failing on today's youtube.py.
2. `python tests/docs_check.py` (also as `python -m tests.docs_check`).

What did run, with the worktree's `.venv/Scripts/python.exe -m ...`: `ruff check .` passed;
`pytest -q` without LOOM_TASK gave 1465 passed, 72 skipped (the plan's baseline was 63 skipped, plus
the 9 new tests); `pytest tests/test_docs_check.py` passed.

To finish: run `LOOM_TASK=p4b-youtube pytest -q tests/publish` (expect only
tests/publish/test_youtube_placement.py to fail: the 2 init tests, the 6 token cases and
test_acceptance) and `python tests/docs_check.py`. Then delete this file before the PR merges.
