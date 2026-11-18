"""CSO P2-1, P2-2, P2-4 and P2-6 on Workflow A (task p2-weekly-hardening, docs/threat-model.md section 6).

P2-1: the key-holding job installs only hash-checked packages. P2-2: open-pr pushes only new,
id-named scripts. P2-4: a read-only job re-checks the queue before the PR opens. P2-6: runs never
overlap. The open-pr tests run its `run:` steps under bash in a scratch git repo, with a local bare
remote and a fake `gh`, so they need bash and git (Linux CI).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests import workflow_rules as rules
from tests.test_weekly_workflow import job_run, job_steps, uses, workflow

ROOT = Path(__file__).resolve().parent.parent
HASHED = ROOT / "requirements-generate.txt"
# What pydantic 2.14 and soundfile 0.14 pull in (Requires-Dist). Update when either is bumped.
TRANSITIVE = {"pydantic-core", "annotated-types", "typing-extensions", "typing-inspection", "cffi",
              "pycparser"}
REQUIREMENT = re.compile(r"([A-Za-z0-9_.-]+)==(\S+)((?:\s+--hash=sha256:[0-9a-f]{64})+)")
NEW = "queue/approved/new-case.json"
OLD = "queue/approved/old-case.json"


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: Path, hashed: bool) -> dict[str, str]:
    """name -> version for every requirement line; each line must be pinned (and hashed if asked)."""
    assert path.is_file(), f"{path.name} is missing"
    found = {}
    for line in path.read_text(encoding="utf-8").replace("\\\n", " ").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = REQUIREMENT.fullmatch(line) if hashed else re.fullmatch(r"([A-Za-z0-9_.-]+)==(\S+)", line)
        assert match, f"{path.name}: '{line}' is not pinned" + (" with sha256 hashes" if hashed else "")
        found[normalise(match.group(1))] = match.group(2)
    return found


def needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def test_hashed_requirements_pin_every_package() -> None:
    hashed = pins(HASHED, hashed=True)
    direct = pins(ROOT / "requirements.txt", hashed=False)
    for name, version in direct.items():
        assert hashed.get(name) == version, f"{name}: requirements-generate.txt differs from requirements.txt"
    assert TRANSITIVE <= set(hashed), TRANSITIVE - set(hashed)


def test_key_job_installs_only_hashed_packages() -> None:
    run = job_run(workflow(), "generate")
    assert "--require-hashes" in run and "-r requirements-generate.txt" in run
    assert "requirements.txt" not in run, "the unhashed file never installs where the key is"


def test_validate_job_rechecks_the_queue_without_credentials() -> None:
    wf = workflow()
    assert set(wf["jobs"]) == {"generate", "validate", "open-pr"}
    job = wf["jobs"]["validate"]
    assert needs(job) == ["generate"]
    assert "validate" in needs(wf["jobs"]["open-pr"])
    assert job.get("permissions", rules.READ_ONLY) == rules.READ_ONLY
    assert "secrets" not in str(job).lower()
    assert not rules.TOKEN_REF.search(str(job)) and "GH_TOKEN" not in str(job)
    assert uses(wf, "validate", "actions/checkout") and uses(wf, "validate", "actions/download-artifact")
    for checkout in uses(wf, "validate", "actions/checkout"):
        assert checkout["with"]["persist-credentials"] is False
    run = job_run(wf, "validate")
    assert "--require-hashes" in run and "-r requirements-generate.txt" in run
    assert "pytest" in run and "tests/test_queue_scripts.py" in run
    assert "pipeline.script.batch" not in run


def test_runs_never_overlap() -> None:
    assert workflow().get("concurrency") == {"group": "weekly-scripts", "cancel-in-progress": False}


BASH = shutil.which("bash") or "bash"
bash_and_git = pytest.mark.skipif(
    sys.platform == "win32" or not shutil.which("bash") or not shutil.which("git"),
    reason="runs the open-pr shell steps; needs bash and git on Linux (CI)")
HERMETIC = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                             *args], cwd=cwd, env={**os.environ, **HERMETIC}, check=True,
                            capture_output=True, text=True, timeout=60)
    return result.stdout


def write(path: Path, text: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def checkout_with_artifact(tmp_path: Path) -> tuple[Path, Path, str]:
    """A clone of a remote whose main holds one approved script, after the artifact landed: one new
    script and pr_body.md. Returns the work tree, the bare remote and the base commit."""
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    write(repo / OLD)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "remote", "add", "origin", str(remote))
    write(repo / NEW)
    write(repo / "out" / "batch" / "pr_body.md", "body\n")
    return repo, remote, git(repo, "rev-parse", "HEAD").strip()


def run_open_pr(tmp_path: Path, repo: Path) -> int:
    """Runs every `run:` step of open-pr in order, as GitHub does (`bash -e`), with step env values
    that are expressions replaced by a dummy. Returns the first non-zero exit code, else 0."""
    bin_dir = tmp_path / "bin"
    write(bin_dir / "gh", '#!/bin/sh\necho "$@" >> "$GH_LOG"\n')
    (bin_dir / "gh").chmod(0o755)
    base_env = {**os.environ, **HERMETIC, "GH_LOG": str(tmp_path / "gh.log"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    for number, step in enumerate(job_steps(workflow(), "open-pr")):
        if "run" not in step:
            continue
        script = tmp_path / f"step{number}.sh"
        script.write_text(str(step["run"]), encoding="utf-8")
        step_env = step.get("env") or {}
        env = {**base_env, **{k: "dummy" if "${{" in str(v) else str(v) for k, v in step_env.items()}}
        result = subprocess.run([BASH, "-e", script.as_posix()], cwd=repo, env=env, capture_output=True,
                                text=True, timeout=120)
        if result.returncode:
            return result.returncode
    return 0


def pushed(remote: Path, base: str) -> dict[str, set[str]]:
    """Each branch on the remote with the files it changes against `base`."""
    branches = git(remote, "for-each-ref", "--format=%(refname)", "refs/heads").split()
    return {b: set(filter(None, git(remote, "diff", "--name-only", "-z", base, b).split("\0")))
            for b in branches}


@bash_and_git
def test_open_pr_pushes_only_the_new_script(tmp_path: Path) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    assert run_open_pr(tmp_path, repo) == 0
    [(branch, files)] = pushed(remote, base).items()
    assert branch.startswith("refs/heads/scripts/")
    assert files == {NEW}
    assert "pr create" in (tmp_path / "gh.log").read_text(encoding="utf-8")


@bash_and_git
@pytest.mark.parametrize("change", ["edit", "delete"])
def test_open_pr_refuses_a_changed_approved_script(tmp_path: Path, change: str) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    if change == "edit":
        write(repo / OLD, '{"edited": true}\n')
    else:
        (repo / OLD).unlink()
    assert run_open_pr(tmp_path, repo) != 0
    assert pushed(remote, base) == {}
    assert not (tmp_path / "gh.log").exists()


@bash_and_git
@pytest.mark.parametrize("name", ["Bad-Case.json", "bad_case.json", "a--b.json", "-x.json",
                                  "case.json.txt", "run.sh", "sub/case.json"])
def test_open_pr_never_pushes_a_badly_named_file(tmp_path: Path, name: str) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    write(repo / "queue" / "approved" / name)
    run_open_pr(tmp_path, repo)
    for files in pushed(remote, base).values():
        assert files == {NEW}


def test_acceptance() -> None:
    """The key job and the validate job install from hashed pins that match requirements.txt; a
    read-only, keyless validate job runs the queue check before open-pr; runs never overlap. The
    open-pr shell tests above must also pass in CI."""
    test_hashed_requirements_pin_every_package()
    test_key_job_installs_only_hashed_packages()
    test_validate_job_rechecks_the_queue_without_credentials()
    test_runs_never_overlap()
