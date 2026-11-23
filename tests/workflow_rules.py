"""Shared structure checks for GitHub Actions workflow files (spec.md section 5)."""

import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def load(name: str, directory: Path = WORKFLOWS) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((directory / name).read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as the boolean True.
    if True in data:
        data["on"] = data.pop(True)
    return data


def steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def run_text(workflow: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in steps(workflow))


READ_ONLY = {"contents": "read"}
# The only exceptions to the rules below, keyed by (workflow file, job id). Locked: widening one
# is an Architect decision. A secret never goes to a job that can write (test_workflow_safety.py).
WRITE_JOBS: dict[tuple[str, str], dict[str, str]] = {
    ("weekly_scripts.yml", "open-pr"): {"contents": "write", "pull-requests": "write"},
    ("daily_publish.yml", "claim"): {"contents": "write"},
    ("daily_publish.yml", "record"): {"contents": "write"},
}
SECRET_JOBS: dict[tuple[str, str], set[str]] = {
    ("weekly_scripts.yml", "generate"): {"GEMINI_API_KEY"},
    ("daily_publish.yml", "upload"): {"YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"},
}
# Owner decision O1 option (b): the YouTube secrets are environment secrets behind a main-only
# deployment rule. The job must name exactly this environment (a plain string), and no other job
# may name one.
ENVIRONMENT_JOBS: dict[tuple[str, str], str] = {
    ("daily_publish.yml", "upload"): "youtube",
}
# Expressions are case-insensitive. A bare `secrets` (toJSON(secrets), secrets['X'], `secrets:
# inherit`) has no name group, so it never matches an allowlist entry.
SECRET_REF = re.compile(r"\bsecrets\b(?:\s*\.\s*([A-Za-z_]\w*))?", re.IGNORECASE)
TOKEN_REF = re.compile(r"\bgithub\s*(?:\.\s*token\b|\[\s*['\"]token)", re.IGNORECASE)


def workflow_files(directory: Path = WORKFLOWS) -> list[Path]:
    """Every file GitHub would run from `directory`; both extensions count."""
    return sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])


def strings(node: Any) -> list[str]:
    """Every key and string value in a parsed YAML tree."""
    if isinstance(node, dict):
        return [s for key, value in node.items() for s in strings(key) + strings(value)]
    if isinstance(node, list):
        return [s for item in node for s in strings(item)]
    return [node] if isinstance(node, str) else []


def reference_problems(where: str, node: Any, secrets: set[str], token: bool) -> list[str]:
    found = []
    for text in strings(node):
        for match in SECRET_REF.finditer(text):
            if (match.group(1) or "").upper() not in secrets:
                found.append(f"{where}: secret reference '{match.group(0)}' is not allowlisted")
        if not token and TOKEN_REF.search(text):
            found.append(f"{where}: github.token is allowed only in an allowlisted write job")
    return found


def job_problems(name: str, job_id: str, job: dict[str, Any]) -> list[str]:
    where, key = f"{name} {job_id}", (name, job_id)
    found = []
    permissions = job.get("permissions", READ_ONLY)
    if permissions not in (READ_ONLY, WRITE_JOBS.get(key, READ_ONLY)):
        found.append(f"{where}: permissions {permissions} are not allowlisted for this job")
    environment, expected = job.get("environment"), ENVIRONMENT_JOBS.get(key)
    if environment != expected:
        found.append(f"{where}: environment {environment!r} must be {expected!r}")
    job_steps = job.get("steps", [])
    for uses in [job.get("uses")] + [step.get("uses") for step in job_steps]:
        if uses and not str(uses).startswith("./") and not PINNED.match(str(uses)):
            found.append(f"{where}: {uses} is not pinned to a full commit SHA")
    for step in job_steps:
        if "${{" in str(step.get("run", "")):
            found.append(f"{where}: expression inside run: {step.get('name')}")
        found += reference_problems(f"{where} run", step.get("run", ""), set(), key in WRITE_JOBS)
        checkout = str(step.get("uses", "")).startswith("actions/checkout@")
        persists = (step.get("with") or {}).get("persist-credentials") is not False
        if checkout and persists and key not in WRITE_JOBS:
            found.append(f"{where}: checkout must set persist-credentials: false")
    secrets = {s.upper() for s in SECRET_JOBS.get(key, set())}
    return found + reference_problems(where, job, secrets, key in WRITE_JOBS)


def safety_problems(workflow: dict[str, Any], name: str) -> list[str]:
    """Read-only token at workflow level, job permissions, secrets and environment only as
    allowlisted for (name, job id), no pull_request_target, third-party actions and reusable
    workflows pinned to a commit SHA, no `${{ }}` inside `run:` (pass values through `env:`), and
    checkouts that keep no credentials except in an allowlisted write job."""
    found = []
    if workflow.get("permissions") != READ_ONLY:
        found.append(f"{name}: workflow permissions must be exactly contents: read")
    if "pull_request_target" in (workflow.get("on") or {}):
        found.append(f"{name}: pull_request_target is not allowed")
    top = {key: value for key, value in workflow.items() if key != "jobs"}
    found += reference_problems(f"{name} workflow", top, set(), False)
    for job_id, job in workflow["jobs"].items():
        found += job_problems(name, job_id, job)
    return found


def directory_problems(directory: Path = WORKFLOWS) -> list[str]:
    files = workflow_files(directory)
    if not files:
        return [f"{directory}: no workflow files found"]
    return [p for path in files for p in safety_problems(load(path.name, directory), path.name)]


def assert_safe(workflow: dict[str, Any], name: str = "") -> None:
    """safety_problems as an assertion. Without `name` no allowlist entry applies."""
    found = safety_problems(workflow, name)
    assert not found, "\n".join(found)


TORCH_INDEX = "--index-url https://download.pytorch.org/whl/cpu"
# The heavy set as a plain pin list, or as the hashed lock the render paths install (p4b-render-lock).
HEAVY_INSTALLS = ("-r requirements-heavy.txt", "-r requirements-render.txt")


def assert_torch_from_cpu_index_first(run: str) -> None:
    """In one `run:` text, torch is installed from the PyTorch CPU index alone, without its
    dependencies, before the heavy requirements. Those, torch's pinned dependencies included, then
    resolve from PyPI only (no extra index, no dependency confusion)."""
    assert "--extra-index-url" not in run
    installs = [line for line in run.splitlines() if "pip install" in line]
    torch = [i for i, line in enumerate(installs) if "--no-deps" in line and TORCH_INDEX in line]
    heavy = [i for i, line in enumerate(installs) if any(r in line for r in HEAVY_INSTALLS)]
    assert torch and heavy, "torch and the heavy requirements are installed"
    assert torch[0] < heavy[0]
    assert "--index-url" not in installs[heavy[0]], "the heavy requirements come from PyPI only"


def model_cache_keys(workflow: dict[str, Any]) -> list[str]:
    caches = [s for s in steps(workflow) if str(s.get("uses", "")).startswith("actions/cache@")]
    return [str(s["with"]["key"]) for s in caches]


def assert_model_cache_tracks_pins(workflow: dict[str, Any]) -> None:
    """The model cache key changes whenever the heavy pins or the weight revision change."""
    keys = model_cache_keys(workflow)
    assert keys, "model weights must be cached"
    assert any("requirements-heavy.txt" in k and "pipeline/constants.py" in k for k in keys)
