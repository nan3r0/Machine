# ENV_ISSUE: p4b-ledger-contracts

The task deletes two files, both in its `paths_allowed`. The session may only change files with Edit and Write, which cannot delete, and `git rm -q tests/test_published_records.py` was refused ("This command requires approval", non-interactive session).

Run in this worktree, then commit on `docs/p4b-ledger-contracts`:

```
git rm -q tests/test_published_records.py
git rm -q data/published/.gitkeep
```

Until then `tests/test_published_records.py` fails 9 tests: its fixtures build records without `run_id` and `run_attempt`, which the schema now requires. Every other test passes (evidence in `.harness/handoffs/p4b-ledger-contracts.md`). Delete this file after the two removals.
