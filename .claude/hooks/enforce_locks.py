"""PreToolUse hook: block edits to locked paths and to paths outside the task scope.

The current task comes from the LOOM_TASK environment variable, set when the
session is launched, so the agent cannot change it from inside the session.

- Admin files (hooks, settings, agent definitions) are always blocked unless the
  session was launched with LOOM_ADMIN=1 by the owner.
- No LOOM_TASK (planning sessions): .harness/locks.yaml is enforced.
- LOOM_TASK set: the edit must match the task's paths_allowed. Locked paths and
  harness files stay blocked unless the task's role owns the contracts.
- Windows path forms that can alias another path (8.3 names, trailing dots or
  spaces, alternate data streams) are blocked; symlinks and junctions are resolved.
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
# Matched against the resolved absolute path, so they also cover ~/.claude, parent repos and worktrees.
ADMIN_PATHS = [
    "*/.claude/hooks/*",
    "*/.claude/settings*.json",
    "*/.claude/agents/*",
]
DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\", "//?/", "//./")
HARNESS_PATHS = [
    ".harness/locks.yaml",
    ".harness/config.yaml",
    ".harness/status.yaml",
    ".harness/tasks/**",
]


def block(message: str) -> NoReturn:
    print(f"BLOCKED by enforce_locks: {message}", file=sys.stderr)
    sys.exit(2)


def is_aliasing_form(raw: str) -> bool:
    """True for Windows path forms that can point at a different, protected path."""
    if raw.startswith(DEVICE_PREFIXES):
        return True
    _, rest = os.path.splitdrive(raw)
    if ":" in rest:
        return True
    parts = rest.replace("\\", "/").split("/")
    return any("~" in p or (p not in (".", "..") and p.endswith((".", " "))) for p in parts)


def resolve(root: Path, raw: str) -> tuple[str, str | None]:
    """(resolved absolute path, project-relative path or None if outside), both lowercase posix."""
    if is_aliasing_form(raw):
        block(f"path form not allowed ({raw}): device prefixes, 8.3 names, trailing dots or spaces "
              "and ':' streams can alias protected files. Use the plain full path.")
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    full = os.path.normcase(os.path.realpath(path))
    base = os.path.normcase(os.path.realpath(root))
    full_posix = Path(full).as_posix().lower()
    if full != base and not full.startswith(base + os.sep):
        return full_posix, None
    return full_posix, Path(os.path.relpath(full, base)).as_posix().lower()


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


def check(root: Path, full: str, rel: str | None, task_id: str, admin: bool) -> None:
    if not admin and matches(full, ADMIN_PATHS):
        block(f"{full} is a Claude Code hook, settings or agent file. Only the owner edits it, in a "
              "session launched with LOOM_ADMIN=1.")

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
    task_id = os.environ.get("LOOM_TASK", "").strip()
    admin = os.environ.get("LOOM_ADMIN") == "1"
    check(root, *resolve(root, raw), task_id, admin)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must block, not allow
        block(f"hook error ({type(exc).__name__}: {exc}). Edit not allowed.")
