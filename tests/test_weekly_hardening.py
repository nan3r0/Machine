"""CSO P2-1, P2-2, P2-4 and P2-6 on Workflow A (task p2-weekly-hardening, docs/threat-model.md section 6).

P2-1: the key-holding job installs only hash-checked packages. P2-2: open-pr pushes only new,
id-named scripts. P2-4: a read-only job re-checks the queue before the PR opens. P2-6: runs never
overlap. The open-pr tests run its `run:` steps under bash in a scratch git repo, with a local bare
remote and a fake `gh`, so they need bash and git (Linux CI).

Review round 1 (security): the artifact is untrusted, so validate and open-pr download it to
`${{ runner.temp }}/artifact`, never over the checkout, and one shared step copies only new, regular,
id-named `queue/approved/*.json` files into the workspace before pytest or any git command.

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
# What pydantic 2.14 and soundfile 0.14 pull in on the runner: the full `pip download` resolve of
# requirements.txt for manylinux x86_64, CPython 3.12, on 2026-11-18. Update when either is bumped.
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
    installs = [line for line in job_run(workflow(), "generate").splitlines() if "pip install" in line]
    assert installs, "the generate job installs its packages"
    for line in installs:
        assert "--require-hashes" in line and "-r requirements-generate.txt" in line, line
        assert "requirements.txt" not in line, "the unhashed file never installs where the key is"


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


RUNNER_TEMP = re.compile(r"\$\{\{\s*runner\.temp\s*\}\}")


@pytest.mark.parametrize("job", ["validate", "open-pr"])
def test_artifact_never_lands_on_the_checkout(job: str) -> None:
    downloads = uses(workflow(), job, "actions/download-artifact")
    assert downloads, f"{job} downloads the artifact"
    for step in downloads:
        path = str((step.get("with") or {}).get("path", ""))
        assert RUNNER_TEMP.sub("RT", path).rstrip("/") == "RT/artifact", f"{job}: path {path!r}"


def test_validate_job_is_explicitly_read_only_and_uncached() -> None:
    wf = workflow()
    assert wf["jobs"]["validate"].get("permissions") == rules.READ_ONLY, "state contents: read"
    for step in uses(wf, "validate", "actions/setup-python"):
        assert "cache" not in (step.get("with") or {}), "validate never restores generate's pip cache"


def run_steps(job: str) -> list[str]:
    return [str(step["run"]) for step in job_steps(workflow(), job) if "run" in step]


def test_validate_copies_the_artifact_with_the_open_pr_step() -> None:
    validate, open_pr = run_steps("validate"), run_steps("open-pr")
    shared = [i for i, run in enumerate(validate) if run in open_pr]
    assert shared, "validate reuses open-pr's filtered copy step, text for text"
    pytest_step = next(i for i, run in enumerate(validate) if "pytest" in run and "pip" not in run)
    assert shared[0] < pytest_step, "the copy runs before pytest"
    copy = open_pr.index(validate[shared[0]])
    push = next(i for i, run in enumerate(open_pr) if "git push" in run)
    assert copy < push and "git push" not in open_pr[copy], "open-pr copies before any commit"
    [copy_step] = [s for s in job_steps(workflow(), "open-pr") if s.get("run") == open_pr[copy]]
    assert "GH_TOKEN" not in (copy_step.get("env") or {}), "the copy step never holds the token"


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
    """A clone of a remote whose main holds one approved script, plus the downloaded artifact in
    `<tmp>/runner/artifact`: the unchanged old script (generate uploads the whole folder), one new
    script and pr_body.md. The checkout itself stays clean. Returns the work tree, the bare remote
    and the base commit."""
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    shutil.copy(ROOT / ".gitignore", repo / ".gitignore")
    write(repo / OLD)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "remote", "add", "origin", str(remote))
    artifact = tmp_path / "runner" / "artifact"
    write(artifact / OLD)
    write(artifact / NEW)
    write(artifact / "out" / "batch" / "pr_body.md", "body\n")
    return repo, remote, git(repo, "rev-parse", "HEAD").strip()


def artifact_of(tmp_path: Path) -> Path:
    return tmp_path / "runner" / "artifact"


def run_open_pr(tmp_path: Path, repo: Path) -> int:
    """Runs every `run:` step of open-pr in order, as GitHub does (`bash -e`), with RUNNER_TEMP set
    and `${{ runner.temp }}` in step env resolved to it; any other expression becomes a dummy.
    Returns the first non-zero exit code, else 0."""
    bin_dir = tmp_path / "bin"
    write(bin_dir / "gh", '#!/bin/sh\necho "$@" >> "$GH_LOG"\n')
    (bin_dir / "gh").chmod(0o755)
    runner = str(tmp_path / "runner")
    base_env = {**os.environ, **HERMETIC, "GH_LOG": str(tmp_path / "gh.log"), "RUNNER_TEMP": runner,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    for number, step in enumerate(job_steps(workflow(), "open-pr")):
        if "run" not in step:
            continue
        script = tmp_path / f"step{number}.sh"
        script.write_text(str(step["run"]), encoding="utf-8")
        step_env = {k: RUNNER_TEMP.sub(lambda _: runner, str(v)) for k, v in (step.get("env") or {}).items()}
        env = {**base_env, **{k: "dummy" if "${{" in v else v for k, v in step_env.items()}}
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
    [create] = [line for line in (tmp_path / "gh.log").read_text(encoding="utf-8").splitlines()
                if "pr create" in line]
    assert f"--body-file {artifact_of(tmp_path)}/" in create, "the PR body is read from the temp folder"
    assert not (repo / "out").exists(), "nothing but queue/approved/*.json reaches the checkout"


@bash_and_git
def test_open_pr_refuses_an_edited_approved_script(tmp_path: Path) -> None:
    # A script missing from the artifact deletes nothing now (it is never extracted over the
    # checkout), so only an edit is a case.
    repo, remote, base = checkout_with_artifact(tmp_path)
    write(artifact_of(tmp_path) / OLD, '{"edited": true}\n')
    assert run_open_pr(tmp_path, repo) != 0
    assert pushed(remote, base) == {}
    assert not (tmp_path / "gh.log").exists()


@bash_and_git
@pytest.mark.parametrize("name", ["Bad-Case.json", "bad_case.json", "a--b.json", "-x.json",
                                  "case.json.txt", "run.sh", "sub/case.json", "café.json",
                                  ".hidden.json"])
def test_open_pr_never_pushes_a_badly_named_file(tmp_path: Path, name: str) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    write(artifact_of(tmp_path) / "queue" / "approved" / name)
    run_open_pr(tmp_path, repo)
    for files in pushed(remote, base).values():
        assert files == {NEW}


@bash_and_git
@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_open_pr_refuses_a_non_regular_file(tmp_path: Path, kind: str) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    odd = artifact_of(tmp_path) / "queue" / "approved" / "odd-case.json"
    if kind == "symlink":
        odd.symlink_to(repo / ".git" / "config")
    elif kind == "directory":
        write(odd / "inner.json")
    else:
        os.mkfifo(odd)
    assert run_open_pr(tmp_path, repo) != 0
    assert pushed(remote, base) == {}
    assert not (tmp_path / "gh.log").exists()


@bash_and_git
def test_open_pr_ignores_files_outside_queue_approved(tmp_path: Path) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    config = (repo / ".git" / "config").read_text(encoding="utf-8")
    planted = [".git/hooks/pre-commit", ".git/config", "conftest.py", "pytest.py", "pyproject.toml",
               "tests/test_queue_scripts.py", "queue/inbox/x-case.json"]
    for name in planted:
        write(artifact_of(tmp_path) / name)
    run_open_pr(tmp_path, repo)
    assert (repo / ".git" / "config").read_text(encoding="utf-8") == config
    for name in planted[2:] + [".git/hooks/pre-commit"]:
        assert not (repo / name).exists(), f"{name} reached the checkout"
    for files in pushed(remote, base).values():
        assert files == {NEW}


@bash_and_git
def test_open_pr_runs_no_git_hooks(tmp_path: Path) -> None:
    repo, remote, base = checkout_with_artifact(tmp_path)
    marker = tmp_path / "hook-ran"
    for hook in ("pre-commit", "commit-msg", "post-checkout", "post-commit", "pre-push",
                 "reference-transaction"):
        write(repo / ".git" / "hooks" / hook, f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
        (repo / ".git" / "hooks" / hook).chmod(0o755)
    assert run_open_pr(tmp_path, repo) == 0
    assert not marker.exists(), "git ran a hook in the job that holds the write token"
    assert list(pushed(remote, base).values()) == [{NEW}]


def test_acceptance() -> None:
    """The key job and the validate job install from hashed pins that match requirements.txt; a
    read-only, keyless, uncached validate job runs the queue check before open-pr; runs never
    overlap; neither later job extracts the artifact over its checkout, and both copy it in with the
    same step. The open-pr shell tests above must also pass in CI."""
    test_hashed_requirements_pin_every_package()
    test_key_job_installs_only_hashed_packages()
    test_validate_job_rechecks_the_queue_without_credentials()
    test_runs_never_overlap()
    for job in ("validate", "open-pr"):
        test_artifact_never_lands_on_the_checkout(job)
    test_validate_job_is_explicitly_read_only_and_uncached()
    test_validate_copies_the_artifact_with_the_open_pr_step()
