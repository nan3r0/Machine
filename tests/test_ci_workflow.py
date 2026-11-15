"""Gate 1 runner (ci.yml), Makefile and Dependabot structure. Owned by no task, so always runs."""

import re
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


def test_ci_installs_torch_from_cpu_index_only_then_pypi() -> None:
    for job in rules.load("ci.yml")["jobs"].values():
        run = "\n".join(str(s.get("run", "")) for s in job["steps"])
        if "requirements-heavy.txt" in run:
            rules.assert_torch_from_cpu_index_first(run)


def test_ci_model_cache_key_tracks_weight_pins() -> None:
    rules.assert_model_cache_tracks_pins(rules.load("ci.yml"))


def test_ci_checkout_keeps_no_credentials() -> None:
    for job in rules.load("ci.yml")["jobs"].values():
        checkout = job["steps"][0]
        assert checkout["uses"].startswith("actions/checkout@")
        assert checkout["with"]["persist-credentials"] is False


def test_ci_scope_check_uses_pr_base_or_main() -> None:
    wf = rules.load("ci.yml")
    env = wf["jobs"]["check"]["env"]
    assert env["BRANCH"] == "${{ github.head_ref || github.ref_name }}"
    assert env["BASE_REF"] == "${{ github.base_ref }}"
    text = rules.run_text(wf)
    assert 'base="${BASE_REF:-main}"' in text
    assert 'git show "origin/$base:tests/scope_check.py"' in text
    assert "git fetch" not in text, "checkout has no credentials; fetch-depth 0 already has origin/*"
    assert '[ "$BRANCH" = "task/p1-contracts" ]' in text, "only the bootstrap PR may use its own checker"
    assert '|| { echo "origin/$base not found" >&2; exit 1; }' in text, "a missing base must say so"
    assert wf["jobs"]["check"]["steps"][0]["with"]["fetch-depth"] == 0
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


def test_makefile_audits_only_project_requirements() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pip-audit -r requirements.txt -r requirements-heavy.txt " in makefile
    assert "requirements-dev" not in makefile


def test_makefile_ignores_only_the_known_setuptools_advisories() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ignored = re.findall(r"--ignore-vuln (\S+)", makefile)
    assert sorted(ignored) == ["GHSA-xmj3-9gf7-h52w", "PYSEC-2026-3447"]


def test_ci_upgrades_setuptools_before_any_install() -> None:
    steps = rules.load("ci.yml")["jobs"]["check"]["steps"]
    runs = [str(s.get("run", "")) for s in steps]
    first = next(i for i, r in enumerate(runs) if "pip install" in r)
    assert 'pip install -q "setuptools>=84.1.0"' in runs[first]


def test_dependabot_watches_pip_and_actions() -> None:
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert {u["package-ecosystem"] for u in config["updates"]} == {"pip", "github-actions"}


def test_requirements_are_pinned_exactly() -> None:
    for name in ("requirements.txt", "requirements-dev.txt", "requirements-heavy.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("--"):
                assert "==" in line or " @ https://" in line, f"{name}: {line} is not pinned"


def test_torch_dependencies_are_pinned() -> None:
    """torch installs with --no-deps, so its dependencies must be pinned for PyPI to supply them."""
    # Requires-Dist of the torch 2.11.0+cpu wheel (torchaudio declares none), plus mpmath (sympy)
    # and markupsafe (jinja2). Update this list when torch is bumped.
    needed = {"filelock", "typing-extensions", "setuptools", "sympy", "mpmath", "networkx", "jinja2",
              "markupsafe", "fsspec"}
    text = (ROOT / "requirements-heavy.txt").read_text(encoding="utf-8")
    pinned = set(re.findall(r"^([A-Za-z0-9_.-]+)==", text, flags=re.MULTILINE))
    assert needed <= {name.lower() for name in pinned}, needed - pinned


def test_requirements_use_no_extra_index_and_hash_direct_urls() -> None:
    for name in ("requirements.txt", "requirements-dev.txt", "requirements-heavy.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            assert "index-url" not in line, f"{name}: package indexes belong in the CI install step"
            if " @ https://" in line:
                assert re.search(r"#sha256=[0-9a-f]{64}$", line), f"{name}: {line} has no sha256"
