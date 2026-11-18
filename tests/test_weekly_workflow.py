"""R13.2, R13.3: Workflow A, weekly_scripts.yml (task p2-weekly-workflow, CSO P1-1 and P1-6).

The safety rules come from tests/workflow_rules.py with the file name, so the per-job allowlists
for this file apply and nothing wider (p2-entry-ci).
"""

from typing import Any

from tests import workflow_rules as rules

NAME = "weekly_scripts.yml"


def workflow() -> dict[str, Any]:
    return rules.load(NAME)


def job_steps(wf: dict[str, Any], job: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = wf["jobs"][job]["steps"]
    return steps


def job_run(wf: dict[str, Any], job: str) -> str:
    return "\n".join(str(step.get("run", "")) for step in job_steps(wf, job))


def uses(wf: dict[str, Any], job: str, action: str) -> list[dict[str, Any]]:
    return [s for s in job_steps(wf, job) if str(s.get("uses", "")).split("@")[0] == action]


def test_triggers() -> None:
    on = workflow()["on"]
    assert on["schedule"] == [{"cron": "0 6 * * 0"}]
    assert "workflow_dispatch" in on
    assert not (on["workflow_dispatch"] or {}).get("inputs"), "vacation-mode counts are deferred (D8)"
    assert set(on) == {"schedule", "workflow_dispatch"}


def test_safe_with_this_files_allowlist() -> None:
    rules.assert_safe(workflow(), NAME)
    assert rules.directory_problems() == []


def test_two_jobs_split_secret_from_write() -> None:
    wf = workflow()
    # p2-weekly-hardening (CSO P2-4) adds a read-only `validate` job; tests/test_weekly_hardening.py
    # pins the exact set once that task is done.
    assert {"generate", "open-pr"} <= set(wf["jobs"]) <= {"generate", "validate", "open-pr"}
    assert wf["permissions"] == {"contents": "read"}
    assert wf["jobs"]["generate"].get("permissions", rules.READ_ONLY) == rules.READ_ONLY
    assert wf["jobs"]["open-pr"]["permissions"] == {"contents": "write", "pull-requests": "write"}
    needs = wf["jobs"]["open-pr"]["needs"]
    needs = [needs] if isinstance(needs, str) else needs
    assert "generate" in needs and set(needs) <= {"generate", "validate"}


def test_generate_job() -> None:
    wf = workflow()
    keyed = [s for s in job_steps(wf, "generate") if "GEMINI_API_KEY" in (s.get("env") or {})]
    assert len(keyed) == 1, "the key is in exactly one step's env"
    assert "python -m pipeline.script.batch sources queue" in str(keyed[0].get("run", ""))
    assert "GEMINI_API_KEY" not in (wf["jobs"]["generate"].get("env") or {})
    for checkout in uses(wf, "generate", "actions/checkout"):
        assert checkout["with"]["persist-credentials"] is False
    run = job_run(wf, "generate")
    assert "requirements-heavy" not in run and "torch" not in run
    [upload] = uses(wf, "generate", "actions/upload-artifact")
    assert int(upload["with"]["retention-days"]) <= 3
    assert "queue/approved" in str(upload["with"]["path"]) and "pr_body.md" in str(upload["with"]["path"])


def test_open_pr_job() -> None:
    wf = workflow()
    job = wf["jobs"]["open-pr"]
    assert "secrets" not in str(job).lower()
    assert uses(wf, "open-pr", "actions/download-artifact")
    run = job_run(wf, "open-pr")
    assert "scripts/" in run
    assert "git push" in run
    assert "gh pr create" in run and "--body-file" in run
    assert "queue/approved" in run
    assert "pipeline.script.batch" not in run, "model output never runs where the write token is"
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "github.token"):
        assert name not in run, f"{name} in a run line"


def test_acceptance() -> None:
    """Sunday 06:00 UTC and by hand; the key only in the read-only generate job; only open-pr writes,
    with no secret; the file passes the p2-entry-ci rules with its own allowlist."""
    test_triggers()
    test_safe_with_this_files_allowlist()
    test_two_jobs_split_secret_from_write()
    test_generate_job()
    test_open_pr_job()
