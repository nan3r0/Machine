"""R16: Workflow B, daily_publish.yml (task p4-daily-workflow, plan .harness/handoffs/p4-plan.md).

Structure tests only, each true both for the first workflow (ledger on main) and for the ledger
branch design (.harness/handoffs/p4b-plan.md, "P1-2 design"). The shell tests of the claim, upload
guard and record steps are in tests/test_daily_publish_ledger.py.

Contract, beyond the task notes:
- Job outputs: render `script_id` and `script_blob` (`git hash-object` of the rendered script),
  upload `video_id` and `sent`, as the youtube CLI writes them. Steps read them only through `env:`
  values of the form `${{ needs.<job>.outputs.<name> }}`.
- claim and record run no step-level `if:`; they branch in shell. Every `run:` step in them that
  calls git turns hooks off with `GIT_CONFIG_*` env (`core.hooksPath=/dev/null`).
- claim and upload refuse unless the script's blob equals `script_blob`. Render runs on main only,
  so a branch run publishes nothing.
"""

import re
from typing import Any

from tests import workflow_rules as rules

NAME = "daily_publish.yml"
SECRETS = {"YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"}
OUTPUT_REF = re.compile(r"^\$\{\{\s*needs\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}$")
RUNNER_TEMP = re.compile(r"\$\{\{\s*runner\.temp\s*\}\}")
PUSH = re.compile(r"\bgit\b.*\bpush\b")


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
    assert "python -m pipeline.publish.pick queue " in run
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


def hooks_off(step: dict[str, Any]) -> bool:
    env = {str(k): str(v) for k, v in (step.get("env") or {}).items()}
    pairs = {(env.get(f"GIT_CONFIG_KEY_{i}"), env.get(f"GIT_CONFIG_VALUE_{i}"))
             for i in range(int(env.get("GIT_CONFIG_COUNT", "0")))}
    return ("core.hooksPath", "/dev/null") in pairs


def test_write_jobs_run_no_pipeline_code() -> None:
    for name in ("claim", "record"):
        run = job_run(name)
        assert "python" not in run and "pip " not in run, "nothing from the repo runs where the token is"
        assert PUSH.search(run), f"{name} pushes"
        for step in job(name)["steps"]:
            assert "if" not in step, f"{name}: branch in shell, not with a step if"
            if re.search(r"\bgit\b", str(step.get("run", ""))):
                assert hooks_off(step), f"{name}: {step.get('name')} runs git with hooks on"


def test_claim_job() -> None:
    run = job_run("claim")
    assert "git hash-object" in run and "jq" in run
    assert "pull --rebase" in run


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


def test_acceptance() -> None:
    """R16.1 to R16.4: daily 14:07 UTC and by hand, never overlapping; four jobs, the YouTube
    secrets only in the read-only upload job behind the youtube environment, the write jobs with no
    secret, no pipeline code and no git hooks; the upload job installs hashed packages only and
    never extracts the artifact over its checkout. The shell tests in
    tests/test_daily_publish_ledger.py must also pass in CI once its task is done."""
    test_triggers_and_concurrency()
    test_safe_with_this_files_allowlist()
    test_four_jobs_split_secret_from_write()
    test_render_job()
    test_write_jobs_run_no_pipeline_code()
    test_claim_job()
    test_upload_job()
