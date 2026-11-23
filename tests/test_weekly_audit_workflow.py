"""Audit F7: the weekly audit, weekly_audit.yml (task p4b-weekly-audit, plan p4b-plan.md "Weekly audit").

A red run is the alert, so every rule here must pass on today's main. The safety rules come from
tests/workflow_rules.py with the file name; this file has no allowlist entry, so nothing is wider
than a read-only token.
"""

import re
from typing import Any

from tests import workflow_rules as rules

NAME = "weekly_audit.yml"
PR_PATHS = {"requirements*.txt", "Makefile", f".github/workflows/{NAME}"}
# The licence rule: any GNU GPL or AGPL licence fails, LGPL and UNKNOWN pass. pip-licenses'
# own --fail-on cannot express it: its partial match is a plain substring, so "GPL-3.0" also hits
# "LGPL-3.0-only". The workflow applies this regex to every row's License field.
RULE = r"(?i)\bA?GPL|GNU (Affero )?General Public"
# phonemizer-fork 3.3.2 (GPLv3+, pulled in by misaki[en]) was accepted at p1-audit: GPL duties
# apply to distribution, and no GPL file is tracked or distributed. Pinned to the version, so a
# bump is checked again.
ACCEPTED_GPL = ["phonemizer-fork:3.3.2"]


def workflow() -> dict[str, Any]:
    return rules.load(NAME)


def job_run(job: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def only_job_running(wf: dict[str, Any], command: str) -> dict[str, Any]:
    [job] = [job for job in wf["jobs"].values() if command in job_run(job)]
    return job


def dev_pin(package: str) -> str:
    text = (rules.WORKFLOWS.parent.parent / "requirements-dev.txt").read_text(encoding="utf-8")
    [pin] = re.findall(rf"^{re.escape(package)}==\S+", text, flags=re.MULTILINE)
    return pin


def test_rule_fails_gpl_and_agpl_only() -> None:
    """Strings from the last reports artifact's licenses.md, plus the SPDX forms."""
    fails = ["GNU General Public License v3 or later (GPLv3+)", "GNU General Public License v2 (GPLv2)",
             "GPL-2.0-only", "GPL-3.0-or-later", "GPLv3", "AGPL-3.0-only",
             "GNU Affero General Public License v3", "gpl-3.0"]
    passes = ["GNU Library or Lesser General Public License (LGPL)",
              "GNU Lesser General Public License v3 (LGPLv3)", "LGPL-2.1-or-later", "LGPL-3.0-only",
              "lgpl-3.0", "UNKNOWN", "MIT License", "Apache-2.0", "BSD-3-Clause"]
    for licence in fails:
        assert re.search(RULE, licence), licence
    for licence in passes:
        assert not re.search(RULE, licence), licence


def test_triggers() -> None:
    on = workflow()["on"]
    assert set(on) == {"schedule", "workflow_dispatch", "pull_request"}, "no push"
    [schedule] = on["schedule"]
    minute, hour, day, month, weekday = schedule["cron"].split()
    assert 1 <= int(minute) <= 59, "off the full hour, where scheduled runs queue up"
    assert 0 <= int(hour) <= 23
    assert (day, month) == ("*", "*")
    assert re.fullmatch(r"[0-6]", weekday), "once a week"
    assert set(on["pull_request"]) == {"paths"}
    assert set(on["pull_request"]["paths"]) == PR_PATHS


def test_safe_read_only_and_without_secrets() -> None:
    wf = workflow()
    rules.assert_safe(wf, NAME)
    assert rules.directory_problems() == []
    for allowlist in (rules.WRITE_JOBS, rules.SECRET_JOBS, rules.ENVIRONMENT_JOBS):
        assert not [key for key in allowlist if key[0] == NAME]
    assert wf["permissions"] == rules.READ_ONLY
    for job in wf["jobs"].values():
        assert "permissions" not in job and "environment" not in job
    text = str(wf).lower()
    assert "secrets" not in text and "github.token" not in text


def test_concurrency_never_cancels() -> None:
    """A cancelled run is not red. GitHub also cancels a pending run in a shared group without
    cancel-in-progress (ci.yml), so a scheduled run gets its own group."""
    concurrency = workflow()["concurrency"]
    assert "github.run_id" in concurrency["group"]
    assert not concurrency.get("cancel-in-progress")


def test_every_job_uses_ci_python() -> None:
    """pip-audit's resolution and the installed set depend on the interpreter, so both jobs use
    the Python version Gate 1 runs on."""
    def python_versions(wf: dict[str, Any]) -> list[str]:
        return [str(step["with"]["python-version"]) for job in wf["jobs"].values() for step in job["steps"]
                if str(step.get("uses", "")).startswith("actions/setup-python@")]

    [ci_version, *_] = python_versions(rules.load("ci.yml"))
    wf = workflow()
    assert python_versions(wf) == [ci_version] * len(wf["jobs"])
    for job in wf["jobs"].values():
        setups = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/setup-python@")]
        assert len(setups) == 1


def test_runs_the_shared_pip_audit_command() -> None:
    job = only_job_running(workflow(), "make audit")
    run = job_run(job)
    assert dev_pin("pip-audit") in run
    assert "pip-licenses" not in run
    assert "pip-audit -r" not in run, "the command and its ignores live in the Makefile"


def test_licence_check_installs_the_runtime_set_only() -> None:
    """requirements.txt, then the heavy set as ci.yml installs it, plus pip-licenses at its pin.
    No dev tools and no pip-audit, so their licences do not count."""
    run = job_run(only_job_running(workflow(), "pip-licenses"))
    installs = [line for line in run.replace("\\\n", " ").splitlines() if "pip install" in line]
    assert 'pip install -q "setuptools>=84.1.0"' in installs[0]
    rules.assert_torch_from_cpu_index_first(run)
    assert any("-r requirements.txt" in line for line in installs)
    assert dev_pin("pip-licenses") in run
    assert "requirements-dev" not in run
    assert "pip-audit" not in run and "make audit" not in run


def test_licence_rule_is_pinned_and_exact() -> None:
    run = job_run(only_job_running(workflow(), "pip-licenses"))
    assert RULE in run
    lines = run.replace("\\\n", " ").splitlines()
    [report] = [line for line in lines if line.lstrip().startswith("pip-licenses")]
    assert "|" not in report, "a pipe without pipefail hides the pip-licenses exit code"
    assert "--fail-on" not in report and "--allow-only" not in report
    [ignored] = re.findall(r"--ignore-packages((?:\s+(?!-)[\w.:-]+)+)", report)
    assert ignored.split() == ACCEPTED_GPL


def test_no_finding_hides_another() -> None:
    """lessons.md 2026-11-16: every step after the first report runs unless cancelled, and
    nothing hides an exit code."""
    for job in workflow()["jobs"].values():
        assert "needs" not in job, "a red audit job must not skip the licence check"
        steps = job["steps"]
        reports = [i for i, s in enumerate(steps) if any(c in str(s.get("run", "")) for c in
                                                         ("make audit", "pip-licenses --", RULE))]
        assert reports
        for step in steps[reports[0] + 1:]:
            assert "!cancelled()" in str(step.get("if", "")), step.get("name")
        for step in steps:
            assert "continue-on-error" not in step
            assert "|| true" not in str(step.get("run", ""))
    assert "continue-on-error" not in str(workflow())


def test_acceptance() -> None:
    """Weekly off the hour, by hand, and on PRs that touch the requirements, the Makefile or this
    workflow; read-only with no secret; `make audit` and the pinned licence rule over the runtime
    set; no finding hides another."""
    test_rule_fails_gpl_and_agpl_only()
    test_triggers()
    test_safe_read_only_and_without_secrets()
    test_concurrency_never_cancels()
    test_every_job_uses_ci_python()
    test_runs_the_shared_pip_audit_command()
    test_licence_check_installs_the_runtime_set_only()
    test_licence_rule_is_pinned_and_exact()
    test_no_finding_hides_another()
