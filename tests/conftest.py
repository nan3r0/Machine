"""Task-aware test selection (owner decision 2026-11-15). Locked.

Each test file listed under `tests:` in a task YAML (.harness/tasks/**) belongs to that task. Its
tests run only when the task is in `done` in .harness/status.yaml or is the current LOOM_TASK, so
main stays green while tasks are unbuilt. Test files no task lists always run.

A LOOM_TASK that names no task fails the run, the same fail-closed rule as the lock hook.
Tests marked `heavy` (ffmpeg, torch, Kokoro) run only when CI=true; locally they skip.
"""

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _tasks() -> list[dict[str, Any]]:
    return [_load_yaml(p) for p in sorted((ROOT / ".harness" / "tasks").glob("**/*.yaml"))]


def _active_tasks() -> set[str]:
    status = ROOT / ".harness" / "status.yaml"
    done = (_load_yaml(status).get("done") or []) if status.exists() else []
    current = os.environ.get("LOOM_TASK", "").strip()
    return set(done) | ({current} if current else set())


def pytest_configure(config: pytest.Config) -> None:
    current = os.environ.get("LOOM_TASK", "").strip()
    if current and current not in {task.get("id") for task in _tasks()}:
        raise pytest.UsageError(
            f"LOOM_TASK={current} matches no task in .harness/tasks/. Fix the launch, not the tests."
        )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    owners = {test: task["id"] for task in _tasks() for test in task.get("tests") or []}
    active = _active_tasks()
    run_heavy = os.environ.get("CI") == "true"
    for item in items:
        rel = Path(os.path.relpath(item.path, ROOT)).as_posix()
        owner = owners.get(rel)
        if owner is not None and owner not in active:
            item.add_marker(pytest.mark.skip(
                reason=f"task {owner} is not done (.harness/status.yaml) and is not LOOM_TASK"))
        elif item.get_closest_marker("heavy") and not run_heavy:
            item.add_marker(pytest.mark.skip(reason="heavy: runs only in CI (CI=true)"))
