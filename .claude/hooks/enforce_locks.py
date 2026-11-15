"""PreToolUse hook: block edits to locked paths and to paths outside the task scope.

The current task comes from the LOOM_TASK environment variable, set when the
session is launched, so the agent cannot change it from inside the session.

- No LOOM_TASK (planning sessions): only .harness/locks.yaml is enforced.
- LOOM_TASK set: the edit must match the task's paths_allowed. Locked paths and
  harness files stay blocked unless the task's role owns the contracts.
- Anything unexpected (unknown task, unreadable YAML, crash) blocks the edit.
  Exit code 2 blocks and sends stderr back to the agent; exit code 1 would not.
"""

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CONTRACT_OWNER_ROLES = {"architect", "test_author"}
HARNESS_PATHS = [
    ".harness/locks.yaml",
    ".harness/config.yaml",
    ".harness/status.yaml",
    ".harness/tasks/**",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/hooks/**",
]


def block(message: str) -> NoReturn:
    print(f"BLOCKED by enforce_locks: {message}", file=sys.stderr)
    sys.exit(2)


def relative_path(root: Path, raw: str) -> str | None:
    """Project-relative, lowercase posix path, or None if outside the project."""
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    full = os.path.normcase(os.path.normpath(path))
    base = os.path.normcase(os.path.normpath(root))
    if full != base and not full.startswith(base + os.sep):
        return None
    return Path(os.path.relpath(full, base)).as_posix().lower()


def matches(rel: str, patterns: list[str]) -> bool:
    # ponytail: fnmatch's "*" also crosses "/", so patterns are slightly lenient.
    return any(fnmatch.fnmatchcase(rel, p.lower()) for p in patterns)


def load_yaml(path: Path) -> dict:
    import yaml  # imported here so a missing PyYAML hits the fail-closed handler

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def find_task(root: Path, task_id: str) -> dict:
    for path in sorted((root / ".harness" / "tasks").glob("*/*.yaml")):
        task = load_yaml(path)
        if task.get("id") == task_id:
            return task
    block(f"LOOM_TASK={task_id} matches no task in .harness/tasks/. Fix the launch, not the hook.")


def check(root: Path, rel: str | None, task_id: str) -> None:
    lock_file = root / ".harness" / "locks.yaml"
    locked = (load_yaml(lock_file).get("locked") or []) if lock_file.exists() else []
    locked_msg = (f"{rel} is locked in .harness/locks.yaml. Do not edit contracts or tests. "
                  "If one is wrong, write CONTRACT_CHANGE.md explaining why and stop.")

    if not task_id:
        if rel is not None and matches(rel, locked):
            block(locked_msg)
        return

    task = find_task(root, task_id)
    if rel is None:
        block("path is outside the project, so it is outside paths_allowed.")
    if rel in (f".harness/handoffs/{task_id.lower()}.md", "contract_change.md", "env_issue.md"):
        return
    owner = task.get("role") in CONTRACT_OWNER_ROLES
    if not owner and matches(rel, locked):
        block(locked_msg)
    if not owner and matches(rel, HARNESS_PATHS):
        block(f"{rel} is a harness file. Implementers never edit it.")
    if not matches(rel, task.get("paths_allowed") or []):
        block(f"{rel} is outside paths_allowed for {task_id}. Stay in scope, or explain the need "
              "in your handoff and stop.")


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in EDIT_TOOLS:
        return
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    check(root, relative_path(root, raw), os.environ.get("LOOM_TASK", "").strip())


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must block, not allow
        block(f"hook error ({type(exc).__name__}: {exc}). Edit not allowed.")
