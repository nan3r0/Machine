"""R16: Workflow B, daily_publish.yml (task p4-daily-workflow, plan .harness/handoffs/p4-plan.md).

Structure tests read the file; the claim and record tests run those jobs' `run:` steps under bash
in a scratch git repo with a local bare remote, so they need bash, git and jq (Linux CI).

Contract for the shell steps, beyond the task notes:
- Job outputs: render `script_id` and `script_blob` (`git hash-object` of the rendered script),
  upload `video_id` and `sent` (`true` or `false`), as the youtube CLI writes them. Steps read
  them only through `env:` values of the form `${{ needs.<job>.outputs.<name> }}`; the runner
  below resolves exactly those, plus
  `${{ runner.temp }}`, and turns every other expression into a dummy.
- claim and record run no step-level `if:`; they branch in shell. Their checkouts use `ref: main`,
  since the claim commit lands on main after the run started.
- claim and record re-check every id they are handed before using it.
- Records are append-only (R16.3). claim fails, with no push, when main already holds
  `data/published/<id>.json` or no longer holds `queue/approved/<id>.json`. record fails, with no
  push, unless main holds a claim-only record for the id. Releasing a claim on `sent=false` exits 0:
  the upload job has already failed the run.
- One version end to end (p4-plan, Ledger): claim and upload refuse unless the script's blob equals
  `script_blob`, and claim writes it as `script_sha`; record moves the script only when its blob
  equals the record's `script_sha`. Render runs on main only, so a branch run publishes nothing.
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
from tests.script.scripts import make_script

NAME = "daily_publish.yml"
ROOT = Path(__file__).resolve().parent.parent
ID = "the-bloop"
SCRIPT = f"queue/approved/{ID}.json"
RECORD = f"data/published/{ID}.json"
VIDEO = "dQw4w9WgXcQ"
SECRETS = {"YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"}


def workflow() -> dict[str, Any]:
    return rules.load(NAME)


def job(name: str) -> dict[str, Any]:
    found: dict[str, Any] = workflow()["jobs"][name]
    return found


def job_run(name: str) -> str:
    return "\n".join(str(step.get("run", "")) for step in job(name).get("steps", []))


def uses(name: str, action: str) -> list[dict[str, Any]]:
    return [s for s in job(name).get("steps", []) if str(s.get("uses", "")).split("@")[0] == action]


def needs(name: str) -> set[str]:
    value = job(name).get("needs", [])
    return {value} if isinstance(value, str) else set(value)


def test_triggers_and_concurrency() -> None:
    wf = workflow()
    assert wf["on"]["schedule"] == [{"cron": "7 14 * * *"}]
    assert not (wf["on"]["workflow_dispatch"] or {}).get("inputs")
    assert set(wf["on"]) == {"schedule", "workflow_dispatch"}
    assert wf.get("concurrency") == {"group": "daily-publish", "cancel-in-progress": False}


def test_safe_with_this_files_allowlist() -> None:
    rules.assert_safe(workflow(), NAME)
    assert rules.directory_problems() == []


def test_four_jobs_split_secret_from_write() -> None:
    assert set(workflow()["jobs"]) == {"render", "claim", "upload", "record"}
    assert needs("claim") == {"render"}
    assert {"render", "claim"} <= needs("upload")
    assert {"render", "claim", "upload"} <= needs("record")
    condition = " ".join(str(job("record").get("if", "")).split())
    assert "always()" in condition and "needs.claim.result == 'success'" in condition
    for name in ("render", "upload"):
        assert job(name).get("permissions", rules.READ_ONLY) == rules.READ_ONLY
    for name in ("claim", "record"):
        assert job(name)["permissions"] == {"contents": "write"}
        assert "secrets" not in str(job(name)).lower()
    assert job("upload")["environment"] == "youtube"


def test_render_job() -> None:
    assert "secrets" not in str(job("render")).lower()
    run = job_run("render")
    assert "python -m pipeline.publish.pick queue data/published" in run
    assert "python -m pipeline.render_one" in run
    rules.assert_torch_from_cpu_index_first(run)
    rules.assert_model_cache_tracks_pins(workflow())
    assert "git hash-object" in run
    assert {"script_id", "script_blob"} <= set(job("render").get("outputs") or {})
    assert " ".join(str(job("render").get("if", "")).split()) == "github.ref == 'refs/heads/main'"
    [upload] = uses("render", "actions/upload-artifact")
    path = str(upload["with"]["path"]).strip()
    assert "\n" not in path and path.endswith("final.mp4"), "the artifact is final.mp4 only"
    assert int(upload["with"]["retention-days"]) == 1
    for checkout in uses("render", "actions/checkout"):
        assert checkout["with"]["persist-credentials"] is False


@pytest.mark.parametrize("name", ["claim", "record"])
def test_write_jobs_run_no_pipeline_code(name: str) -> None:
    run = job_run(name)
    assert "python" not in run and "pip " not in run, "nothing from the repo runs where the token is"
    assert "git push" in run
    [checkout] = uses(name, "actions/checkout")
    assert checkout["with"]["ref"] == "main"
    for step in job(name)["steps"]:
        assert "if" not in step, f"{name}: branch in shell, not with a step if"


def test_claim_job() -> None:
    run = job_run("claim")
    assert "git hash-object" in run and "jq" in run
    assert "pull --rebase" in run


RUNNER_TEMP = re.compile(r"\$\{\{\s*runner\.temp\s*\}\}")


def test_upload_job() -> None:
    keyed = [s for s in job("upload")["steps"] if set(s.get("env") or {}) & SECRETS]
    assert len(keyed) == 1 and set(keyed[0]["env"]) >= SECRETS, "the secrets are in exactly one step's env"
    assert "python -m pipeline.publish.youtube" in str(keyed[0]["run"])
    assert "GITHUB_OUTPUT" in str(keyed[0]["run"])
    blob_ref = OUTPUT_REF.match(str(keyed[0]["env"].get("SCRIPT_BLOB", "")).strip())
    assert blob_ref is not None and blob_ref.groups() == ("render", "script_blob")
    upload_run = str(keyed[0]["run"])
    assert "git hash-object" in upload_run and "$SCRIPT_BLOB" in upload_run
    assert upload_run.index("git hash-object") < upload_run.index("python -m pipeline.publish.youtube"), \
        "the script version is checked before anything is sent"
    installs = [line for line in job_run("upload").splitlines() if "pip install" in line]
    assert installs
    for line in installs:
        assert "--require-hashes" in line and "-r requirements-generate.txt" in line, line
    run = job_run("upload")
    assert "requirements-heavy" not in run and "torch" not in run
    for checkout in uses("upload", "actions/checkout"):
        assert checkout["with"]["persist-credentials"] is False
    [download] = uses("upload", "actions/download-artifact")
    path = str((download.get("with") or {}).get("path", ""))
    assert RUNNER_TEMP.sub("RT", path).rstrip("/").startswith("RT/"), "never over the checkout"
    assert {"video_id", "sent"} <= set(job("upload").get("outputs") or {})
    for step in uses("upload", "actions/setup-python"):
        assert "cache" not in (step.get("with") or {}), "the secret job restores no cache"
    for step in job("upload")["steps"]:
        assert not str(step.get("uses", "")).startswith("actions/cache"), "the secret job restores no cache"


BASH = shutil.which("bash") or "bash"
shell_tools = pytest.mark.skipif(
    sys.platform == "win32" or not all(shutil.which(tool) for tool in ("bash", "git", "jq")),
    reason="runs the claim and record shell steps; needs bash, git and jq on Linux (CI)")
HERMETIC = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
OUTPUT_REF = re.compile(r"^\$\{\{\s*needs\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}$")


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
                            cwd=cwd, env={**os.environ, **HERMETIC}, check=True, capture_output=True,
                            text=True, timeout=60)
    return result.stdout


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def remote_with_script(tmp_path: Path) -> Path:
    """A bare remote whose main holds one approved script and the empty ledger folder."""
    remote, seed = tmp_path / "remote.git", tmp_path / "seed"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(seed))
    shutil.copy(ROOT / ".gitignore", seed / ".gitignore")
    put(seed / SCRIPT, make_script(id=ID).model_dump_json().encode("utf-8") + b"\n")
    put(seed / "data" / "published" / ".gitkeep", b"")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "base")
    git(seed, "push", "-q", str(remote), "main")
    return remote


def checkout(tmp_path: Path, remote: Path, name: str) -> Path:
    """What actions/checkout with `ref: main` and kept credentials gives a write job."""
    repo = tmp_path / name
    git(tmp_path, "clone", "-q", "-b", "main", str(remote), str(repo))
    return repo


def run_job(tmp_path: Path, repo: Path, name: str, outputs: dict[str, str]) -> int:
    """Runs every `run:` step of job `name` in order, as GitHub does (bash -eo pipefail), with
    `needs.<job>.outputs.<name>` env values taken from `outputs` ("job.name" keys, missing ones
    empty, as GitHub gives them). Returns the first non-zero exit code, else 0."""
    runner = tmp_path / "runner"
    runner.mkdir(exist_ok=True)
    base = {**os.environ, **HERMETIC, "RUNNER_TEMP": str(runner),
            "GITHUB_OUTPUT": str(runner / "output"), "GITHUB_STEP_SUMMARY": str(runner / "summary")}

    def resolve(value: Any) -> str:
        text = RUNNER_TEMP.sub(str(runner), str(value))
        match = OUTPUT_REF.match(text.strip())
        if match:
            return outputs.get(f"{match.group(1)}.{match.group(2)}", "")
        return "dummy" if "${{" in text else text

    for number, step in enumerate(job(name)["steps"]):
        if "run" not in step:
            continue
        script = tmp_path / f"{name}-step{number}.sh"
        script.write_text(str(step["run"]), encoding="utf-8")
        env = {**base, **{k: resolve(v) for k, v in (step.get("env") or {}).items()}}
        result = subprocess.run([BASH, "--noprofile", "--norc", "-eo", "pipefail", script.as_posix()],
                                cwd=repo, env=env, capture_output=True, text=True, timeout=120)
        if result.returncode:
            return result.returncode
    return 0


def files(remote: Path) -> set[str]:
    return set(filter(None, git(remote, "ls-tree", "-r", "-z", "--name-only", "main").split("\0")))


def show(remote: Path, path: str) -> str:
    return git(remote, "show", f"main:{path}")


def head(remote: Path) -> str:
    return git(remote, "rev-parse", "main").strip()


def blob(remote: Path) -> str:
    """The approved script's blob on main, as render's `script_blob` output gives it."""
    return git(remote, "rev-parse", f"main:{SCRIPT}").strip()


def claim_outputs(remote: Path) -> dict[str, str]:
    return {"render.script_id": ID, "render.script_blob": blob(remote)}


def record_on_main(remote: Path) -> str | None:
    return show(remote, RECORD) if RECORD in files(remote) else None


def change_main(tmp_path: Path, remote: Path, add: dict[str, bytes], remove: tuple[str, ...] = ()) -> None:
    """Pushes one commit to main from a separate clone, as another run or the owner would."""
    repo = checkout(tmp_path, remote, "change")
    for path, data in add.items():
        put(repo / path, data)
    for path in remove:
        git(repo, "rm", "-q", path)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")
    git(repo, "push", "-q", "origin", "main")


def claimed(tmp_path: Path) -> Path:
    remote = remote_with_script(tmp_path)
    assert run_job(tmp_path, checkout(tmp_path, remote, "claim"), "claim", claim_outputs(remote)) == 0
    return remote


@shell_tools
def test_claim_retries_once_after_a_rejected_push(tmp_path: Path) -> None:
    remote = remote_with_script(tmp_path)
    rendered = claim_outputs(remote)
    repo = checkout(tmp_path, remote, "claim")
    other = checkout(tmp_path, remote, "other")
    put(other / "notes.txt", b"pushed while the run rendered\n")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "concurrent")
    git(other, "push", "-q", "origin", "main")
    assert run_job(tmp_path, repo, "claim", rendered) == 0
    assert {RECORD, "notes.txt"} <= files(remote)


@shell_tools
@pytest.mark.parametrize("bad", ["", "../x", "The-Bloop", "a b", "x;touch pwned", "-rf"])
def test_claim_refuses_a_bad_script_id(tmp_path: Path, bad: str) -> None:
    remote = remote_with_script(tmp_path)
    base = head(remote)
    repo = checkout(tmp_path, remote, "claim")
    outputs = {"render.script_id": bad, "render.script_blob": blob(remote)}
    assert run_job(tmp_path, repo, "claim", outputs) != 0
    assert head(remote) == base
    assert not (repo / "pwned").exists()


@shell_tools
def test_claim_never_claims_what_main_does_not_offer(tmp_path: Path) -> None:
    """At most once: a run queued behind a timed-out upload picked from an older checkout."""
    remote = remote_with_script(tmp_path)
    rendered = claim_outputs(remote)
    change_main(tmp_path, remote, {}, remove=(SCRIPT,))
    base, before = head(remote), record_on_main(remote)
    repo = checkout(tmp_path, remote, "claim")
    assert run_job(tmp_path, repo, "claim", rendered) != 0
    assert (head(remote), record_on_main(remote)) == (base, before)


def edit_script(tmp_path: Path, remote: Path) -> None:
    """The owner re-approves a different version of the script on main."""
    change_main(tmp_path, remote, {SCRIPT: show(remote, SCRIPT).encode("utf-8") + b"\n"})


@shell_tools
@pytest.mark.parametrize("bad", ["", "abc", "0" * 39, "0" * 41, "z" * 40, "$(touch pwned)" + "0" * 26])
def test_claim_refuses_a_bad_script_blob(tmp_path: Path, bad: str) -> None:
    remote = remote_with_script(tmp_path)
    base = head(remote)
    repo = checkout(tmp_path, remote, "claim")
    assert run_job(tmp_path, repo, "claim", {"render.script_id": ID, "render.script_blob": bad}) != 0
    assert head(remote) == base
    assert not (repo / "pwned").exists()


@shell_tools
@pytest.mark.parametrize("changed", ["before-the-claim", "during-the-claim"])
def test_claim_refuses_a_script_version_that_was_not_rendered(tmp_path: Path, changed: str) -> None:
    """during-the-claim: the local check passes, the push is rejected, and the rebase brings the
    new version, so only the re-check after `pull --rebase` can refuse."""
    remote = remote_with_script(tmp_path)
    rendered = claim_outputs(remote)
    if changed == "before-the-claim":
        edit_script(tmp_path, remote)
    repo = checkout(tmp_path, remote, "claim")
    if changed == "during-the-claim":
        edit_script(tmp_path, remote)
    base = head(remote)
    assert blob(remote) != rendered["render.script_blob"]
    assert run_job(tmp_path, repo, "claim", rendered) != 0
    assert head(remote) == base and RECORD not in files(remote)


@shell_tools
def test_record_releases_a_claim_that_sent_nothing(tmp_path: Path) -> None:
    remote = claimed(tmp_path)
    repo = checkout(tmp_path, remote, "record")
    outputs = {"render.script_id": ID, "upload.video_id": "", "upload.sent": "false"}
    assert run_job(tmp_path, repo, "record", outputs) == 0
    assert RECORD not in files(remote) and SCRIPT in files(remote)


@shell_tools
@pytest.mark.parametrize(("video_id", "sent"), [(VIDEO, ""), ("", "false")])
def test_record_needs_a_claim(tmp_path: Path, video_id: str, sent: str) -> None:
    remote = remote_with_script(tmp_path)
    base, before = head(remote), record_on_main(remote)
    repo = checkout(tmp_path, remote, "record")
    outputs = {"render.script_id": ID, "upload.video_id": video_id, "upload.sent": sent}
    assert run_job(tmp_path, repo, "record", outputs) != 0
    assert (head(remote), record_on_main(remote)) == (base, before)


@shell_tools
@pytest.mark.parametrize(("video_id", "sent"), [("", "true"), ("", ""), ("dQw4w9WgXc", ""),
                                                ("dQw4w9WgXc;touch pwned", ""), ("$(touch pwned)xx", "")])
def test_record_leaves_the_claim_when_the_upload_is_unknown(tmp_path: Path, video_id: str, sent: str) -> None:
    remote = claimed(tmp_path)
    claim = head(remote)
    repo = checkout(tmp_path, remote, "record")
    outputs = {"render.script_id": ID, "upload.video_id": video_id, "upload.sent": sent}
    assert run_job(tmp_path, repo, "record", outputs) != 0
    assert head(remote) == claim
    assert not (repo / "pwned").exists()


@shell_tools
@pytest.mark.parametrize("name", ["claim", "record"])
def test_write_jobs_run_no_git_hooks(tmp_path: Path, name: str) -> None:
    remote = remote_with_script(tmp_path) if name == "claim" else claimed(tmp_path)
    outputs = {**claim_outputs(remote), "upload.video_id": VIDEO, "upload.sent": ""}
    repo = checkout(tmp_path, remote, name)
    marker = tmp_path / "hook-ran"
    for hook in ("pre-commit", "commit-msg", "post-commit", "pre-push", "reference-transaction",
                 "post-checkout", "post-merge", "pre-rebase", "post-rewrite"):
        put(repo / ".git" / "hooks" / hook, f"#!/bin/sh\ntouch '{marker}'\nexit 1\n".encode("utf-8"))
        (repo / ".git" / "hooks" / hook).chmod(0o755)
    assert run_job(tmp_path, repo, name, outputs) == 0
    assert not marker.exists(), f"git ran a hook in {name}, which holds the write token"


def test_acceptance() -> None:
    """R16.1 to R16.4: daily 14:07 UTC and by hand, never overlapping; four jobs, the YouTube
    secrets only in the read-only upload job behind the youtube environment, the write jobs with no
    secret and no pipeline code; the upload job installs hashed packages only and never extracts the
    artifact over its checkout. The claim and record shell tests above must also pass in CI."""
    test_triggers_and_concurrency()
    test_safe_with_this_files_allowlist()
    test_four_jobs_split_secret_from_write()
    test_render_job()
    for name in ("claim", "record"):
        test_write_jobs_run_no_pipeline_code(name)
    test_claim_job()
    test_upload_job()
