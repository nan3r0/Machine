"""Shared structure checks for GitHub Actions workflow files (spec.md section 5)."""

import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as the boolean True.
    if True in data:
        data["on"] = data.pop(True)
    return data


def steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def run_text(workflow: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in steps(workflow))


def assert_safe(workflow: dict[str, Any]) -> None:
    """Read-only token, no pull_request_target, third-party actions pinned to a commit SHA,
    and no `${{ }}` expressions inside `run:` scripts (pass them through `env:` instead)."""
    assert workflow.get("permissions") == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}
    assert "pull_request_target" not in (workflow["on"] or {})
    for step in steps(workflow):
        uses = step.get("uses")
        if uses and not uses.startswith("./"):
            assert PINNED.match(uses), f"{uses} is not pinned to a full commit SHA"
        assert "${{" not in str(step.get("run", "")), f"expression inside run: {step.get('name')}"
