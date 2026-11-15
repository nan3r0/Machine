"""Gate 1 runner (ci.yml), Makefile and Dependabot structure. Owned by no task, so always runs."""

from pathlib import Path

import yaml

from tests import workflow_rules as rules

ROOT = Path(__file__).resolve().parent.parent
GATE_TOOLS = ["ruff check", "mypy --strict pipeline/", "pytest", "--cov=pipeline", ".harness/tests", "bandit",
              "semgrep", "gitleaks", "pip-audit", "actionlint"]


def test_ci_is_safe() -> None:
    rules.assert_safe(rules.load("ci.yml"))


def test_ci_runs_on_every_push_and_pr_never_pr_target() -> None:
    on = rules.load("ci.yml")["on"]
    assert {"push", "pull_request", "workflow_dispatch"} <= set(on)
    assert on["push"] is None and on["pull_request"] is None, "no branch filters: every push and PR"


def test_ci_runs_make_check_with_heavy_packages_and_ffmpeg() -> None:
    text = rules.run_text(rules.load("ci.yml"))
    assert "make check" in text
    assert "requirements-heavy.txt" in text
    assert "ffmpeg" in text


def test_ci_scope_check_uses_pr_base_or_main() -> None:
    wf = rules.load("ci.yml")
    env = wf["jobs"]["check"]["env"]
    assert env["BRANCH"] == "${{ github.head_ref || github.ref_name }}"
    assert env["BASE_REF"] == "${{ github.base_ref }}"
    text = rules.run_text(wf)
    assert 'base="${BASE_REF:-main}"' in text
    assert 'git show "origin/$base:tests/scope_check.py"' in text
    assert 'python "$checker" "$BRANCH" "origin/$base"' in text


def test_ci_sets_loom_task_only_for_valid_task_branches() -> None:
    text = rules.run_text(rules.load("ci.yml"))
    assert "task/*)" in text
    assert "^[a-z0-9]+(-[a-z0-9]+)*$" in text
    assert 'echo "LOOM_TASK=$id" >> "$GITHUB_ENV"' in text


def test_ci_checks_binary_checksums() -> None:
    text = rules.run_text(rules.load("ci.yml"))
    assert text.count("sha256sum -c") == 2


def test_report_job_runs_only_by_hand_and_uploads() -> None:
    job = rules.load("ci.yml")["jobs"]["reports"]
    assert job["if"] == "github.event_name == 'workflow_dispatch'"
    text = "\n".join(str(s.get("run", "")) for s in job["steps"])
    for tool in ("mutmut run", "pip-licenses", "pip-audit", "--cov=pipeline"):
        assert tool in text
    assert any(s.get("uses", "").startswith("actions/upload-artifact@") for s in job["steps"])


def test_makefile_check_runs_every_gate_tool() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for tool in GATE_TOOLS:
        assert tool in makefile, tool


def test_dependabot_watches_pip_and_actions() -> None:
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert {u["package-ecosystem"] for u in config["updates"]} == {"pip", "github-actions"}


def test_requirements_are_pinned_exactly() -> None:
    for name in ("requirements.txt", "requirements-dev.txt", "requirements-heavy.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("--"):
                assert "==" in line or " @ https://" in line, f"{name}: {line} is not pinned"
