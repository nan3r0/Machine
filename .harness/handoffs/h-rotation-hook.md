# Handoff: h-rotation-hook

## Goal
Sessions rotate themselves at the context threshold via a Stop hook, so the owner does not watch context.

## Status
partial (code and tests done; awaiting a manual smoke test of the real window launch)

## What changed
- Review round 1 fixes: the launch now runs on the stop after the block (`stop_hook_active` only suppresses a second block); only `LOOM_TASK` or `LOOM_ROLE=orchestrator` sessions are guarded (launcher sets `LOOM_ROLE`); ClosePid job waits for a real `cmd.exe`/`node.exe` child and kills the old PowerShell tree with `taskkill /T /F` after checking the pid is still powershell; config and number errors exit 0 with a stderr line; missing or synthetic model falls back to `roles.implementer`/`roles.orchestrator`; sidechain lines skipped; `.started` is touched once (first block time). 68 tests pass.
- `.harness/scripts/context_guard.py`: new Stop hook. Sums the three input-token fields of the last assistant message, compares with the task or orchestrator threshold, blocks the first crossing (exit 2) and launches the replacement window once the handoff is newer than the `.started` marker. Writes a `.launched` marker so later Stop events do not launch twice.
- `.harness/scripts/open_task_window.ps1`: `-ClosePid`, orchestrator mode (`-Task orchestrator`, no `LOOM_TASK`, title "Loom orchestrator"), exports `LOOM_WINDOW_PID`, clears inherited `LOOM_*` variables, and narrows the Bash allowlist to `-m pytest`, `-m ruff`, `-m mypy` and `-m pip install -r`.
- `.harness/tests/test_context_guard.py`: 13 tests written first (thresholds, stop_hook_active, first crossing message, fresh handoff launch, launch once, malformed or missing input, launch failure).
- `HARNESS.md`: new "Automatic rotation (Stage 0)" part in 7a; section 11 layout lists `scripts/` and `rotate/`.
- `.harness/handoffs/orchestrator.md`: Token rules describe the hook.
- `.gitignore`: `.harness/rotate/`.

## Decisions made (and why)
- The old window's PowerShell pid comes from `LOOM_WINDOW_PID`, set by `open_task_window.ps1`. Walking the process tree from the hook is fragile. A hand-started orchestrator has no such variable, so its old window stays open.
- Model for the replacement comes from the last assistant message in the transcript ("same model"), with config.yaml roles as fallback.
- Launch failure or any unreadable input exits 0 with a stderr line, so the guard never blocks a session.
- The ClosePid job waits until the new window has any child process (up to 60 s), then stops the old PowerShell.
- No toast; the console line is enough.

## Tried and abandoned
- none

## Notes for the architect
- Task YAML step 2 (exit early on `stop_hook_active`) is wrong: that flag is set on the very stop where the launch must happen. Fixed in code; the YAML should be corrected.
- The narrowed Bash allowlist drops `.venv/Scripts/python.exe .harness/log_outcome.py`; confirm task sessions never need it (orchestrator logs outcomes).

## Known risks / fragile spots
- `open_task_window.ps1` and the real window launch are not covered by tests (launcher is monkeypatched; Windows-only). Try it once by hand before relying on it.
- The transcript format (`message.usage`, `message.model` on assistant lines) is assumed from current Claude Code; if it changes, the guard silently stops rotating (exit 0).
- If the hook runs from a different cwd than the worktree, `CLAUDE_PROJECT_DIR` is used first.

## Next step for whoever picks this up
Owner adds this to `.claude/settings.json` (admin step, `LOOM_ADMIN=1`), merged into the existing `hooks` object:

```json
"Stop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR/.venv/Scripts/python.exe\" \"$CLAUDE_PROJECT_DIR/.harness/scripts/context_guard.py\"",
        "timeout": 15
      }
    ]
  }
]
```

Then smoke-test by temporarily setting `rotate_context_pct` to 1 in a throwaway task session.

## Docs
- HARNESS.md: section 7a and section 11 updated in this task.
- `.harness/handoffs/orchestrator.md`: Token rules updated in this task.
- workflow.md / status.yaml: add `h-rotation-hook` as done at close-out.
- lessons.md: none.

## Evidence
- tests: `.venv/Scripts/python.exe -m pytest .harness/tests -q` 68 passed.
- `.venv/Scripts/python.exe -m ruff check .harness` clean.
- .ps1 syntax check and real window launch: not run. Smoke test by hand before relying on it.
