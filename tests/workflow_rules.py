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


TORCH_INDEX_INSTALL = "--no-deps --index-url https://download.pytorch.org/whl/cpu"


def assert_torch_from_cpu_index_first(run: str) -> None:
    """In one `run:` text, torch is installed from the PyTorch CPU index alone, without its
    dependencies, before the heavy requirements. Those, torch's pinned dependencies included, then
    resolve from PyPI only (no extra index, no dependency confusion)."""
    assert "--extra-index-url" not in run
    torch_at = run.index(TORCH_INDEX_INSTALL)
    assert torch_at < run.index("-r requirements-heavy.txt")


def model_cache_keys(workflow: dict[str, Any]) -> list[str]:
    caches = [s for s in steps(workflow) if str(s.get("uses", "")).startswith("actions/cache@")]
    return [str(s["with"]["key"]) for s in caches]


def assert_model_cache_tracks_pins(workflow: dict[str, Any]) -> None:
    """The model cache key changes whenever the heavy pins or the weight revision change."""
    keys = model_cache_keys(workflow)
    assert keys, "model weights must be cached"
    assert any("requirements-heavy.txt" in k and "pipeline/constants.py" in k for k in keys)
