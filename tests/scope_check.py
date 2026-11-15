"""CI scope check for task branches: the server-side twin of .claude/hooks/enforce_locks.py. Locked.

Usage: python tests/scope_check.py <branch> <base-ref>

On a `task/<task-id>` branch, every file changed since the merge base with <base-ref> must be
allowed for that task: inside its paths_allowed (or its own handoff, CONTRACT_CHANGE.md,
ENV_ISSUE.md), not locked unless the task's role owns the contracts, and never a Claude Code
admin file. The task YAML and locks.yaml are read from <base-ref>, so a branch cannot widen its
own scope. Patterns match like the hook: lowercase fnmatch, where `*` also crosses `/`.
"""

import fnmatch
import re
import subprocess
import sys
from typing import Any

import yaml

CONTRACT_OWNER_ROLES = {"architect", "test_author"}
ADMIN_PATHS = [".claude/hooks/*", ".claude/settings*.json", ".claude/agents/*"]
HARNESS_PATHS = [".harness/locks.yaml", ".harness/config.yaml", ".harness/status.yaml", ".harness/tasks/*"]
TASK_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path.lower(), p.lower()) for p in patterns)


def violations(task: dict[str, Any], locked: list[str], changed: list[str]) -> list[str]:
    """One message per changed path the task may not touch."""
    allowed = [*(task.get("paths_allowed") or []), f".harness/handoffs/{task['id']}.md",
               "CONTRACT_CHANGE.md", "ENV_ISSUE.md"]
    owner = task.get("role") in CONTRACT_OWNER_ROLES
    found = []
    for path in changed:
        if matches(path, ADMIN_PATHS):
            found.append(f"{path}: Claude Code admin file, owner-only")
        elif not owner and matches(path, locked):
            found.append(f"{path}: locked in .harness/locks.yaml")
        elif not owner and matches(path, HARNESS_PATHS):
            found.append(f"{path}: harness file, implementers never edit it")
        elif not matches(path, allowed):
            found.append(f"{path}: outside paths_allowed for {task['id']}")
    return found


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def load_at(base: str, path: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(git("show", f"{base}:{path}")) or {}
    return data


def find_task(base: str, task_id: str) -> dict[str, Any] | None:
    for path in git("ls-tree", "-r", "--name-only", base, "--", ".harness/tasks").split():
        if path.endswith(".yaml"):
            task = load_at(base, path)
            if task.get("id") == task_id:
                return task
    return None


def main(argv: list[str]) -> int:
    branch, base = argv
    if not branch.startswith("task/"):
        print(f"scope check skipped: {branch} is not a task/<task-id> branch")
        return 0
    task_id = branch.removeprefix("task/")
    if not TASK_ID.match(task_id):
        print(f"scope check failed: {task_id!r} is not a valid task id")
        return 1
    task = find_task(base, task_id)
    if task is None:
        print(f"scope check failed: no task {task_id} in .harness/tasks/ on {base}")
        return 1
    locked = load_at(base, ".harness/locks.yaml").get("locked") or []
    changed = git("diff", "--name-only", "--no-renames", f"{base}...HEAD").splitlines()
    found = violations(task, locked, changed)
    for message in found:
        print(f"scope violation: {message}")
    print(f"scope check {'failed' if found else 'passed'}: {len(changed)} changed files for {task_id}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
