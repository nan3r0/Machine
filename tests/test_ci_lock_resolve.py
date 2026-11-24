"""ci.yml resolves every hashed lock on each push and PR (task p4c-ci-lock-resolve).

Gate 1 installs requirements*.txt without hashes and never the hashed locks, so Dependabot bumps
that pip cannot resolve (pydantic without pydantic-core, thinc, curated-transformers, rfc3986) merged
green and failed only in a live workflow. The lock-resolve job runs pip on Linux CPython 3.12, the
platform the locks are cut for, the way the workflows install them: the torch lock for real from
the PyTorch CPU index with --no-deps, every other lock with --dry-run and the full resolver.
"""

import copy
from collections.abc import Callable
from typing import Any

import pytest

from tests import workflow_rules as rules
from tests.test_lock_consistency import ROOT, hashed_locks

JOB = "lock-resolve"
TORCH_LOCK = "requirements-render-torch.txt"
# Each of these defeats the check: a second index, a host without TLS checks, or an ignored failure.
FORBIDDEN = ("--extra-index-url", "--trusted-host", "|| true")


def pip_installs(job: dict[str, Any]) -> list[str]:
    """Every `pip install` command line in the job's run steps, continuation lines joined."""
    runs = "\n".join(str(step.get("run", "")) for step in job.get("steps") or [])
    return [line for line in runs.replace("\\\n", " ").splitlines() if "pip install" in line]


def lock_problems(installs: list[str], lock: str) -> list[str]:
    lines = [line for line in installs if f"-r {lock}" in line and "--require-hashes" in line]
    if not lines:
        return [f"{lock}: no pip install with --require-hashes -r {lock}"]
    if lock == TORCH_LOCK:
        if not any("--no-deps" in line and rules.TORCH_INDEX in line for line in lines):
            return [f"{lock}: install it with --no-deps from the PyTorch CPU index alone"]
        return []
    if not any("--dry-run" in line and "--no-deps" not in line for line in lines):
        return [f"{lock}: resolve it with --dry-run and its dependencies (no --no-deps)"]
    return []


def resolve_problems(workflow: dict[str, Any], locks: list[str]) -> list[str]:
    """One message per way the lock-resolve job fails to resolve every lock on every run."""
    job = workflow["jobs"].get(JOB)
    if job is None:
        return [f"ci.yml has no {JOB} job"]
    found = rules.job_problems("ci.yml", JOB, job)
    if "if" in job:
        found.append(f"{JOB}: no job-level if; it must run on every push and PR")
    if job.get("runs-on") != "ubuntu-latest":
        found.append(f"{JOB}: runs-on must be ubuntu-latest, the platform the locks are cut for")
    steps = job.get("steps") or []
    versions = [str((s.get("with") or {}).get("python-version")) for s in steps
                if str(s.get("uses", "")).startswith("actions/setup-python@")]
    if versions != ["3.12"]:
        found.append(f"{JOB}: one setup-python step with python-version 3.12, got {versions}")
    if job.get("continue-on-error") or any(s.get("continue-on-error") for s in steps):
        found.append(f"{JOB}: continue-on-error hides a failed resolve")
    if any("if" in s for s in steps):
        found.append(f"{JOB}: no step-level if; a skipped resolve step passes")
    installs = pip_installs(job)
    found += [f"{JOB}: {bad} in a pip install" for bad in FORBIDDEN if any(bad in i for i in installs)]
    for lock in locks:
        found += lock_problems(installs, lock)
    return found


LOCKS = ["requirements-generate.txt", TORCH_LOCK, "requirements-render.txt"]
VALID_JOB: dict[str, Any] = {
    "runs-on": "ubuntu-latest",
    "timeout-minutes": 30,
    "steps": [
        {"uses": "actions/checkout@" + "a" * 40, "with": {"persist-credentials": False}},
        {"uses": "actions/setup-python@" + "b" * 40, "with": {"python-version": "3.12"}},
        {"name": "Resolve the render locks", "run": (
            'python -m venv "$RUNNER_TEMP/render"\n'
            '"$RUNNER_TEMP/render/bin/python" -m pip install -q --no-deps --require-hashes \\\n'
            f"  {rules.TORCH_INDEX} -r {TORCH_LOCK}\n"
            '"$RUNNER_TEMP/render/bin/python" -m pip install --dry-run --require-hashes \\\n'
            "  -r requirements-render.txt\n")},
        {"name": "Resolve the generate lock", "run": (
            'python -m venv "$RUNNER_TEMP/generate"\n'
            '"$RUNNER_TEMP/generate/bin/python" -m pip install --dry-run --require-hashes \\\n'
            "  -r requirements-generate.txt\n")},
    ],
}


def workflow_with(job: dict[str, Any] | None) -> dict[str, Any]:
    return {"jobs": {"check": {}} | ({JOB: job} if job is not None else {})}


def run_of(job: dict[str, Any], index: int) -> str:
    return str(job["steps"][index]["run"])


BREAKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "gated": lambda j: j.update({"if": "github.event_name == 'workflow_dispatch'"}),
    "secret": lambda j: j.update({"env": {"KEY": "${{ secrets.GEMINI_API_KEY }}"}}),
    "write token": lambda j: j.update({"permissions": {"contents": "write"}}),
    "step gated": lambda j: j["steps"][3].update({"if": "github.event_name == 'workflow_dispatch'"}),
    "windows":lambda j: j.update({"runs-on": "windows-latest"}),
    "python 3.13": lambda j: j["steps"][1]["with"].update({"python-version": "3.13"}),
    "ignored failure": lambda j: j["steps"][3].update({"continue-on-error": True}),
    "or true": lambda j: j["steps"][3].update({"run": run_of(j, 3).replace(".txt\n", ".txt || true\n")}),
    "extra index": lambda j: j["steps"][3].update(
        {"run": run_of(j, 3).replace("--dry-run", "--dry-run --extra-index-url https://example.org")}),
    "generate skipped": lambda j: j["steps"].pop(3),
    "no hashes": lambda j: j["steps"][3].update({"run": run_of(j, 3).replace("--require-hashes ", "")}),
    "no resolve": lambda j: j["steps"][3].update({"run": run_of(j, 3).replace("--dry-run", "--no-deps")}),
    "dry run without deps": lambda j: j["steps"][2].update(
        {"run": run_of(j, 2).replace("--dry-run", "--dry-run --no-deps")}),
    "torch from pypi": lambda j: j["steps"][2].update({"run": run_of(j, 2).replace(rules.TORCH_INDEX, "")}),
}


def test_the_check_passes_a_job_that_resolves_every_lock() -> None:
    assert resolve_problems(workflow_with(VALID_JOB), LOCKS) == []


def test_the_check_flags_a_missing_job() -> None:
    assert resolve_problems(workflow_with(None), LOCKS) == [f"ci.yml has no {JOB} job"]


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_the_check_flags_a_job_that_can_pass_without_resolving(name: str) -> None:
    job = copy.deepcopy(VALID_JOB)
    BREAKS[name](job)
    assert resolve_problems(workflow_with(job), LOCKS), name


def test_acceptance() -> None:
    locks = [p.name for p in hashed_locks(ROOT)]
    assert {"requirements-generate.txt", TORCH_LOCK, "requirements-render.txt"} <= set(locks)
    problems = resolve_problems(rules.load("ci.yml"), locks)
    assert not problems, "\n".join(problems)
