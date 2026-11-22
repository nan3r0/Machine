"""R16 on the ledger branch: Workflow B, daily_publish.yml (task p4b-ledger-workflow, design in
.harness/handoffs/p4b-plan.md, "P1-2 design"; CSO P1-2, P4-1 and P4-2, QA lead rank 3).

Structure tests read the file. The shell tests run job `run:` steps under bash in a scratch
workspace built from the job's own actions/checkout steps, against a local bare remote seeded with
`main` and an orphan `ledger` branch independently of the workflow, so they need bash, git and jq
(Linux CI).

Contract for the shell steps, beyond the task notes:
- A checkout with no `ref` gets main and one with no `path` the workspace root. A checkout with
  `persist-credentials: false` can fetch but not push.
- Steps run as GitHub runs them: `bash -e`, or `bash --noprofile --norc -eo pipefail` under
  `shell: bash`, in the step's or the job's `working-directory`. The runner's default environment
  gives GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT, GITHUB_WORKSPACE, GITHUB_OUTPUT, GITHUB_ENV and
  RUNNER_TEMP. In step `env:` only `${{ needs.<job>.outputs.<name> }}` and `${{ runner.temp }}`
  resolve; every other expression becomes a dummy.
- Job outputs as today: render `script_id` and `script_blob` (the rendered script's git blob),
  upload `video_id`, or `sent` (`true` or `false`) when it has no video id.
- The upload guard is every `run:` step from the one whose name starts "Require this run's claim"
  through the one step holding the YouTube secrets.
- Records are data/published/<id>.json on the ledger, one PublishRecord each. A refusal exits
  non-zero and pushes nothing.
"""

import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from pipeline.schema import PublishRecord
from tests import workflow_rules as rules
from tests.script.scripts import make_script

NAME = "daily_publish.yml"
ROOT = Path(__file__).resolve().parent.parent
ID = "the-bloop"
SCRIPT = f"queue/approved/{ID}.json"
RECORD = f"data/published/{ID}.json"
VIDEO = "dQw4w9WgXcQ"
RUN_ID, RUN_ATTEMPT = 4242, 1
SECRETS = {"YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"}
GUARD = "Require this run's claim"
SCRIPT_BYTES = make_script(id=ID).model_dump_json().encode("utf-8") + b"\n"
# git's blob id, computed here so the expected value does not come from the code under test.
BLOB = hashlib.sha1(b"blob %d\0" % len(SCRIPT_BYTES) + SCRIPT_BYTES, usedforsecurity=False).hexdigest()
RENDERED = {"render.script_id": ID, "render.script_blob": BLOB}
PUBLISHED = {"youtube_video_id": VIDEO, "published_at": "2026-11-22T14:20:00Z"}


def workflow() -> dict[str, Any]:
    return rules.load(NAME)


def job(name: str) -> dict[str, Any]:
    found: dict[str, Any] = workflow()["jobs"][name]
    return found


def job_run(name: str) -> str:
    return "\n".join(str(step.get("run", "")) for step in job(name).get("steps", []))


def uses(name: str, action: str) -> list[dict[str, Any]]:
    return [s for s in job(name).get("steps", []) if str(s.get("uses", "")).split("@")[0] == action]


def checkouts(name: str) -> list[tuple[str, str, bool]]:
    """(ref, path, keeps credentials) per actions/checkout step: "" for no ref, "." for the root."""
    found = []
    for step in uses(name, "actions/checkout"):
        given = step.get("with") or {}
        path = posixpath.normpath(str(given.get("path", "")) or ".")
        found.append((str(given.get("ref", "")), path, given.get("persist-credentials") is not False))
    return found


def upload_guard() -> list[dict[str, Any]]:
    """The upload steps from the claim check through the secret step (P4-2: check first)."""
    steps = job("upload")["steps"]
    [start] = [i for i, s in enumerate(steps) if str(s.get("name", "")).startswith(GUARD)]
    [keyed] = [i for i, s in enumerate(steps) if set(s.get("env") or {}) & SECRETS]
    assert start < keyed, "the claim is checked before the step that holds the secrets"
    assert "run" in steps[start] and not set(steps[start].get("env") or {}) & SECRETS
    return list(steps[start:keyed + 1])


def test_render_picks_against_the_ledger() -> None:
    found = checkouts("render")
    assert ("ledger", "ledger", False) in found
    assert [c for c in found if c[1] == "."] and not [c for c in found if c[2]]
    assert len(found) == 2
    assert "python -m pipeline.publish.pick queue ledger/data/published" in job_run("render")


def test_claim_checkouts() -> None:
    assert sorted(checkouts("claim")) == [("ledger", "ledger", True), ("main", ".", False)]


def test_upload_checkouts_and_guard_order() -> None:
    assert sorted(checkouts("upload")) == [("ledger", "ledger", False), ("main", ".", False)]
    guard = upload_guard()
    assert set(guard[-1]["env"]) >= SECRETS
    assert "python -m pipeline.publish.youtube" in str(guard[-1]["run"])


def test_record_checks_out_only_the_ledger() -> None:
    [(ref, _, keeps)] = checkouts("record")
    assert ref == "ledger" and keeps


PUSH = re.compile(r"\bgit\b.*\bpush\b")


def test_only_claim_and_record_push_and_only_to_the_ledger() -> None:
    for name in workflow()["jobs"]:
        for line in job_run(name).splitlines():
            if PUSH.search(line):
                assert name in ("claim", "record"), f"{name} pushes: {line}"
                assert "ledger" in line and "main" not in line, f"every push names ledger: {line}"
    for name in ("claim", "record"):
        assert PUSH.search(job_run(name)), f"{name} pushes its change to the ledger"


def test_run_ids_come_from_the_runner_environment() -> None:
    wf = workflow()
    for text in rules.strings(wf):
        assert not re.search(r"github\s*\.\s*run_(id|attempt)", text, re.IGNORECASE), text
    for step in rules.steps(wf):
        overridden = [k for k in step.get("env") or {} if str(k).upper().startswith("GITHUB_")]
        assert not overridden, step.get("name")
    guard = "\n".join(str(s.get("run", "")) for s in upload_guard())
    for text in (job_run("claim"), guard):
        assert "GITHUB_RUN_ID" in text and "GITHUB_RUN_ATTEMPT" in text
    assert "GITHUB_RUN_ID" in job_run("record")


BASH = shutil.which("bash") or "bash"
shell_tools = pytest.mark.skipif(
    sys.platform == "win32" or not all(shutil.which(tool) for tool in ("bash", "git", "jq")),
    reason="runs the workflow's shell steps; needs bash, git and jq on Linux (CI)")
HERMETIC = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
OUTPUT_REF = re.compile(r"^\$\{\{\s*needs\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}$")
RUNNER_TEMP = re.compile(r"\$\{\{\s*runner\.temp\s*\}\}")
NO_PUSH = "/nonexistent/no-credentials.git"
HOOKS = ("pre-commit", "commit-msg", "post-commit", "pre-push", "reference-transaction",
         "post-checkout", "post-merge", "pre-rebase", "post-rewrite", "pre-auto-gc")


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
                            cwd=cwd, env={**os.environ, **HERMETIC}, check=True, capture_output=True,
                            text=True, timeout=60)
    return result.stdout


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def record(**changes: Any) -> bytes:
    """A claim-only record for the script as rendered, written by run RUN_ID attempt RUN_ATTEMPT."""
    data = {"script_id": ID, "script_sha": BLOB, "claimed_at": "2026-11-22T14:10:00Z",
            "youtube_video_id": None, "published_at": None, "run_id": RUN_ID, "run_attempt": RUN_ATTEMPT}
    return json.dumps({**data, **changes}).encode("utf-8") + b"\n"


def commit_files(repo: Path, add: dict[str, bytes], links: dict[str, str]) -> None:
    for path, data in add.items():
        put(repo / path, data)
    for path, target in links.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).symlink_to(target)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seed")


def seeded(tmp_path: Path, ledger: dict[str, bytes] | None = None,
           links: dict[str, str] | None = None) -> Path:
    """A bare remote: main holds the approved script; the orphan ledger branch holds
    data/published/.gitkeep, the `ledger` files and the `links` symlinks (path: target)."""
    remote, seed = tmp_path / "remote.git", tmp_path / "seed"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(seed))
    shutil.copy(ROOT / ".gitignore", seed / ".gitignore")
    commit_files(seed, {SCRIPT: SCRIPT_BYTES}, {})
    git(seed, "push", "-q", str(remote), "main")
    git(seed, "checkout", "-q", "--orphan", "ledger")
    git(seed, "rm", "-rfq", ".")
    commit_files(seed, {"data/published/.gitkeep": b"", **(ledger or {})}, links or {})
    git(seed, "push", "-q", str(remote), "ledger")
    return remote


def change(tmp_path: Path, remote: Path, branch: str, add: dict[str, bytes],
           remove: tuple[str, ...] = ()) -> None:
    """Pushes one commit to `branch` from a separate clone, as another run or the owner would."""
    repo = Path(tempfile.mkdtemp(dir=tmp_path))
    git(tmp_path, "clone", "-q", "-b", branch, str(remote), str(repo))
    for path in remove:
        git(repo, "rm", "-q", path)
    commit_files(repo, add, {})
    git(repo, "push", "-q", "origin", branch)


def head(remote: Path, branch: str) -> str:
    return git(remote, "rev-parse", branch).strip()


def files(remote: Path, branch: str) -> set[str]:
    return set(filter(None, git(remote, "ls-tree", "-r", "-z", "--name-only", branch).split("\0")))


def show(remote: Path, branch: str, path: str) -> str:
    return git(remote, "show", f"{branch}:{path}")


def heads(remote: Path) -> tuple[str, str]:
    return head(remote, "main"), head(remote, "ledger")


def changed_since(remote: Path, base: str) -> tuple[int, set[str]]:
    """Commits on the ledger after `base`, and the paths they change."""
    count = int(git(remote, "rev-list", "--count", f"{base}..ledger"))
    return count, set(filter(None, git(remote, "diff", "--name-only", "-z", base, "ledger").split("\0")))


def workspace(tmp_path: Path, remote: Path, name: str) -> Path:
    """What job `name`'s checkout steps give it: each ref cloned at its path, the root first."""
    root = tmp_path / name
    found = sorted(checkouts(name), key=lambda c: c[1] != ".")
    if not any(path == "." for _, path, _ in found):
        root.mkdir()
    for ref, path, keeps in found:
        dest = root / path
        git(tmp_path, "clone", "-q", "-b", ref or "main", str(remote), str(dest))
        if not keeps:
            git(dest, "remote", "set-url", "--push", "origin", NO_PUSH)
    return root


def run_steps(tmp_path: Path, root: Path, name: str, steps: list[dict[str, Any]],
              outputs: dict[str, str], extra: dict[str, str] | None = None) -> int:
    """Runs the `run:` steps in order as GitHub would, with `needs.<job>.outputs.<name>` env values
    from `outputs` ("job.name" keys, missing ones empty) and `extra` over the runner environment.
    Returns the first non-zero exit code, else 0."""
    runner = tmp_path / "runner"
    runner.mkdir(exist_ok=True)
    inherited = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "RUNNER_", "ACTIONS_"))}
    base = {**inherited, **HERMETIC, "GITHUB_WORKSPACE": str(root), "GITHUB_RUN_ID": str(RUN_ID),
            "GITHUB_RUN_ATTEMPT": str(RUN_ATTEMPT), "GITHUB_OUTPUT": str(runner / "output"),
            "GITHUB_ENV": str(runner / "env"), "GITHUB_STEP_SUMMARY": str(runner / "summary"),
            "RUNNER_TEMP": str(runner), **(extra or {})}
    defaults = (job(name).get("defaults") or {}).get("run") or {}

    def resolve(value: Any) -> str:
        text = RUNNER_TEMP.sub(str(runner), str(value))
        match = OUTPUT_REF.match(text.strip())
        if match:
            return outputs.get(f"{match.group(1)}.{match.group(2)}", "")
        return "dummy" if "${{" in text else text

    for number, step in enumerate(steps):
        if "run" not in step:
            continue
        shell = step.get("shell", defaults.get("shell"))
        assert shell in (None, "bash"), f"{name}: unexpected shell {shell}"
        flags = ["--noprofile", "--norc", "-eo", "pipefail"] if shell == "bash" else ["-e"]
        cwd = root / str(step.get("working-directory", defaults.get("working-directory", ".")))
        script = tmp_path / f"{name}-step{number}.sh"
        script.write_text(str(step["run"]), encoding="utf-8")
        env = {**base, **{k: resolve(v) for k, v in (step.get("env") or {}).items()}}
        result = subprocess.run([BASH, *flags, script.as_posix()], cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=120)
        if result.returncode:
            return result.returncode
    return 0


def run_job(tmp_path: Path, remote: Path, name: str, outputs: dict[str, str],
            extra: dict[str, str] | None = None) -> tuple[int, Path]:
    root = workspace(tmp_path, remote, name)
    return run_steps(tmp_path, root, name, job(name)["steps"], outputs, extra), root


def pwned(root: Path) -> bool:
    return (root / "pwned").exists() or (root / "ledger" / "pwned").exists()


# claim


@shell_tools
def test_claim_writes_this_runs_claim_to_the_ledger(tmp_path: Path) -> None:
    remote = seeded(tmp_path)
    main, base = heads(remote)
    code, _ = run_job(tmp_path, remote, "claim", RENDERED,
                      {"GITHUB_RUN_ID": "987654321", "GITHUB_RUN_ATTEMPT": "3"})
    assert code == 0
    assert head(remote, "main") == main, "claim never pushes to main"
    assert changed_since(remote, base) == (1, {RECORD})
    text = show(remote, "ledger", RECORD)
    data = json.loads(text)
    assert type(data["run_id"]) is int and type(data["run_attempt"]) is int, "JSON numbers, not strings"
    claim = PublishRecord.model_validate_json(text)
    assert (claim.script_id, claim.script_sha, claim.run_id, claim.run_attempt) == (ID, BLOB, 987654321, 3)
    assert claim.youtube_video_id is None and claim.published_at is None


@shell_tools
@pytest.mark.parametrize("existing", [{}, PUBLISHED, {"run_id": 1}],
                         ids=["claim-only", "published", "other-run"])
def test_claim_refuses_when_the_ledger_holds_a_record(tmp_path: Path, existing: dict[str, Any]) -> None:
    remote = seeded(tmp_path, {RECORD: record(**existing)})
    before = heads(remote), show(remote, "ledger", RECORD)
    code, _ = run_job(tmp_path, remote, "claim", RENDERED)
    assert code != 0
    assert (heads(remote), show(remote, "ledger", RECORD)) == before


@shell_tools
@pytest.mark.parametrize("how", ["edited", "removed"])
def test_claim_refuses_a_script_main_does_not_hold_as_rendered(tmp_path: Path, how: str) -> None:
    remote = seeded(tmp_path)
    if how == "edited":
        change(tmp_path, remote, "main", {SCRIPT: SCRIPT_BYTES + b"\n"})
    else:
        change(tmp_path, remote, "main", {}, remove=(SCRIPT,))
    before = heads(remote)
    code, _ = run_job(tmp_path, remote, "claim", RENDERED)
    assert code != 0
    assert heads(remote) == before


@shell_tools
@pytest.mark.parametrize("bad", ["", "../x", "The-Bloop", "a b", "x;touch pwned", "-rf"])
def test_claim_refuses_a_bad_script_id(tmp_path: Path, bad: str) -> None:
    remote = seeded(tmp_path)
    before = heads(remote)
    code, root = run_job(tmp_path, remote, "claim", {"render.script_id": bad, "render.script_blob": BLOB})
    assert code != 0
    assert heads(remote) == before
    assert not pwned(root)


@shell_tools
@pytest.mark.parametrize("bad", ["", "abc", "0" * 39, "0" * 41, "z" * 40, "$(touch pwned)" + "0" * 26])
def test_claim_refuses_a_bad_script_blob(tmp_path: Path, bad: str) -> None:
    remote = seeded(tmp_path)
    before = heads(remote)
    code, root = run_job(tmp_path, remote, "claim", {"render.script_id": ID, "render.script_blob": bad})
    assert code != 0
    assert heads(remote) == before
    assert not pwned(root)


@shell_tools
@pytest.mark.parametrize("variable", ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"])
@pytest.mark.parametrize("bad", ["", "12a", "1 2", "-1", "1.5", "$(touch pwned)"])
def test_claim_refuses_a_run_number_that_is_not_a_number(tmp_path: Path, variable: str, bad: str) -> None:
    remote = seeded(tmp_path)
    before = heads(remote)
    code, root = run_job(tmp_path, remote, "claim", RENDERED, {variable: bad})
    assert code != 0
    assert heads(remote) == before
    assert not pwned(root)


@shell_tools
def test_claim_retries_once_after_a_rejected_push(tmp_path: Path) -> None:
    remote = seeded(tmp_path)
    main = head(remote, "main")
    root = workspace(tmp_path, remote, "claim")
    other = "data/published/other-one.json"
    change(tmp_path, remote, "ledger", {other: record(script_id="other-one", run_id=1)})
    assert run_steps(tmp_path, root, "claim", job("claim")["steps"], RENDERED) == 0
    assert {RECORD, other} <= files(remote, "ledger")
    assert head(remote, "main") == main


@shell_tools
def test_claim_refuses_when_another_run_claimed_the_script_first(tmp_path: Path) -> None:
    """The local check passes; the rejected push and the rebase bring the other run's claim."""
    remote = seeded(tmp_path)
    root = workspace(tmp_path, remote, "claim")
    change(tmp_path, remote, "ledger", {RECORD: record(run_id=1)})
    before = heads(remote)
    assert run_steps(tmp_path, root, "claim", job("claim")["steps"], RENDERED) != 0
    assert heads(remote) == before
    assert show(remote, "ledger", RECORD) == record(run_id=1).decode("utf-8")


# upload guard (QA lead rank 3, P4-1, P4-2)


def run_upload(tmp_path: Path, remote: Path, outputs: dict[str, str] = RENDERED,
               extra: dict[str, str] | None = None) -> tuple[int, list[str], Path]:
    """Runs the upload guard with fake python and pip on PATH. Returns the exit code, every fake
    call as its program name followed by its arguments, and the workspace."""
    root = workspace(tmp_path, remote, "upload")
    bin_dir, log = tmp_path / "bin", tmp_path / "calls.log"
    for tool in ("python", "python3", "pip", "pip3"):
        put(bin_dir / tool, b'#!/bin/sh\nprintf "%s\\n" "$(basename "$0")" "$@" >> "$FAKE_LOG"\n')
        (bin_dir / tool).chmod(0o755)
    put(tmp_path / "runner" / "artifact" / "final.mp4", b"not a video")
    env = {"FAKE_LOG": str(log), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", **(extra or {})}
    code = run_steps(tmp_path, root, "upload", upload_guard(), outputs, env)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return code, calls, root


@shell_tools
def test_upload_sends_this_runs_claim(tmp_path: Path) -> None:
    code, calls, _ = run_upload(tmp_path, seeded(tmp_path, {RECORD: record()}))
    runner = tmp_path / "runner"
    assert code == 0
    assert calls == ["python", "-m", "pipeline.publish.youtube", SCRIPT, f"{runner}/artifact/final.mp4",
                     str(runner / "output")]


UPLOAD_REFUSALS: dict[str, tuple[dict[str, bytes], dict[str, str]]] = {
    "no-record": ({}, {}),
    "published": ({RECORD: record(**PUBLISHED)}, {}),
    "other-script-sha": ({RECORD: record(script_sha="0" * 40)}, {}),
    "other-run-id": ({RECORD: record(run_id=RUN_ID + 1)}, {}),
    "re-run": ({RECORD: record()}, {"GITHUB_RUN_ATTEMPT": str(RUN_ATTEMPT + 1)}),
}


@shell_tools
@pytest.mark.parametrize("case", list(UPLOAD_REFUSALS))
def test_upload_refuses_anything_but_this_runs_claim(tmp_path: Path, case: str) -> None:
    ledger, extra = UPLOAD_REFUSALS[case]
    code, calls, _ = run_upload(tmp_path, seeded(tmp_path, ledger), extra=extra)
    assert code != 0
    assert calls == [], "nothing runs, so nothing is sent"


@shell_tools
def test_upload_refuses_a_symlinked_record(tmp_path: Path) -> None:
    remote = seeded(tmp_path, {"data/published/elsewhere.json": record()}, {RECORD: "elsewhere.json"})
    code, calls, _ = run_upload(tmp_path, remote)
    assert code != 0
    assert calls == []


@shell_tools
@pytest.mark.parametrize("bad", ["../x", "x;touch pwned"])
def test_upload_refuses_a_bad_script_id(tmp_path: Path, bad: str) -> None:
    remote = seeded(tmp_path, {RECORD: record()})
    code, calls, root = run_upload(tmp_path, remote, {"render.script_id": bad, "render.script_blob": BLOB})
    assert code != 0
    assert calls == []
    assert not pwned(root)


@shell_tools
def test_upload_refuses_when_main_holds_another_version(tmp_path: Path) -> None:
    """The claim matches the rendered blob, but main's script changed since."""
    remote = seeded(tmp_path, {RECORD: record()})
    change(tmp_path, remote, "main", {SCRIPT: SCRIPT_BYTES + b"\n"})
    code, calls, _ = run_upload(tmp_path, remote)
    assert code != 0
    assert calls == []


# record


def upload_said(video_id: str, sent: str) -> dict[str, str]:
    return {**RENDERED, "upload.video_id": video_id, "upload.sent": sent}


@shell_tools
@pytest.mark.parametrize("attempt", ["1", "2"], ids=["same-attempt", "re-run-of-record"])
def test_record_completes_this_runs_claim(tmp_path: Path, attempt: str) -> None:
    remote = seeded(tmp_path, {RECORD: record()})
    main, base = heads(remote)
    code, _ = run_job(tmp_path, remote, "record", upload_said(VIDEO, ""), {"GITHUB_RUN_ATTEMPT": attempt})
    assert code == 0
    assert head(remote, "main") == main and SCRIPT in files(remote, "main"), "main is never touched"
    assert changed_since(remote, base) == (1, {RECORD})
    text = show(remote, "ledger", RECORD)
    done = PublishRecord.model_validate_json(text)
    assert done.youtube_video_id == VIDEO and done.published_at is not None
    claim, data = json.loads(record()), json.loads(text)
    for key in ("script_id", "script_sha", "claimed_at", "run_id", "run_attempt"):
        assert data[key] == claim[key], key


@shell_tools
def test_record_releases_a_claim_that_sent_nothing(tmp_path: Path) -> None:
    remote = seeded(tmp_path, {RECORD: record()})
    main = head(remote, "main")
    code, _ = run_job(tmp_path, remote, "record", upload_said("", "false"))
    assert code == 0
    assert RECORD not in files(remote, "ledger")
    assert head(remote, "main") == main


@shell_tools
@pytest.mark.parametrize(("video_id", "sent"), [("", "true"), ("", ""), ("dQw4w9WgXc", ""),
                                                ("dQw4w9WgXc;touch pwned", ""), ("$(touch pwned)xx", "")])
def test_record_keeps_the_claim_when_the_upload_is_unknown(tmp_path: Path, video_id: str, sent: str) -> None:
    remote = seeded(tmp_path, {RECORD: record()})
    before = heads(remote)
    code, root = run_job(tmp_path, remote, "record", upload_said(video_id, sent))
    assert code != 0
    assert heads(remote) == before
    assert not pwned(root)


RECORD_REFUSALS: dict[str, dict[str, bytes]] = {
    "no-record": {},
    "published": {RECORD: record(**PUBLISHED)},
    "other-run-id": {RECORD: record(run_id=RUN_ID + 1)},
}


@shell_tools
@pytest.mark.parametrize("case", list(RECORD_REFUSALS))
@pytest.mark.parametrize(("video_id", "sent"), [(VIDEO, ""), ("", "false")], ids=["video", "sent-false"])
def test_record_refuses_anything_but_this_runs_claim(tmp_path: Path, case: str, video_id: str,
                                                     sent: str) -> None:
    remote = seeded(tmp_path, RECORD_REFUSALS[case])
    before = heads(remote), files(remote, "ledger")
    code, _ = run_job(tmp_path, remote, "record", upload_said(video_id, sent))
    assert code != 0
    assert (heads(remote), files(remote, "ledger")) == before


@shell_tools
@pytest.mark.parametrize("bad", ["", "../x", "x;touch pwned", "-rf"])
def test_record_refuses_a_bad_script_id(tmp_path: Path, bad: str) -> None:
    remote = seeded(tmp_path, {RECORD: record()})
    before = heads(remote)
    outputs = {"render.script_id": bad, "upload.video_id": VIDEO, "upload.sent": ""}
    code, root = run_job(tmp_path, remote, "record", outputs)
    assert code != 0
    assert heads(remote) == before
    assert not pwned(root)


@shell_tools
@pytest.mark.parametrize("name", ["claim", "record"])
def test_write_jobs_run_no_git_hooks(tmp_path: Path, name: str) -> None:
    remote = seeded(tmp_path) if name == "claim" else seeded(tmp_path, {RECORD: record()})
    root = workspace(tmp_path, remote, name)
    marker = tmp_path / "hook-ran"
    for git_dir in (root / ".git", root / "ledger" / ".git"):
        if not git_dir.is_dir():
            continue
        for hook in HOOKS:
            put(git_dir / "hooks" / hook, f"#!/bin/sh\ntouch '{marker}'\nexit 1\n".encode("utf-8"))
            (git_dir / "hooks" / hook).chmod(0o755)
    assert run_steps(tmp_path, root, name, job(name)["steps"], upload_said(VIDEO, "")) == 0
    assert not marker.exists(), f"git ran a hook in {name}, which holds the write token"


def test_acceptance() -> None:
    """R16 on the ledger (P1-2, P4-1, P4-2): render picks against the ledger branch; claim checks
    main without credentials and writes to the ledger with them; upload reads both without
    credentials and checks the claim before the one secret step; record touches only the ledger;
    nothing pushes to main; run ids come from the runner. The shell tests above must also pass in
    CI (Linux)."""
    test_render_picks_against_the_ledger()
    test_claim_checkouts()
    test_upload_checkouts_and_guard_order()
    test_record_checks_out_only_the_ledger()
    test_only_claim_and_record_push_and_only_to_the_ledger()
    test_run_ids_come_from_the_runner_environment()
