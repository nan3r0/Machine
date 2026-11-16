"""Every workflow file obeys the safety rules (CSO P1-6, docs/threat-model.md section 4.3).

Each rule is shown failing on a bad workflow in tmp_path, and the clean fixture is shown passing on
its own, so a broken fixture cannot pass as a "blocked" case (lessons.md 2026-11-15).
"""

from pathlib import Path

import pytest

from tests import workflow_rules as rules

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"

# Shaped like the planned weekly_scripts.yml: it uses every allowlisted exception once.
WEEKLY = f"""\
name: weekly scripts
on:
  schedule:
    - cron: "0 6 * * 0"
  workflow_dispatch:
permissions:
  contents: read
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA}
        with:
          persist-credentials: false
      - name: Generate
        env:
          GEMINI_API_KEY: ${{{{ secrets.GEMINI_API_KEY }}}}
        run: python -m pipeline.script.batch sources queue out/batch
  open-pr:
    needs: generate
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@{SHA}
      - name: Open PR
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: gh pr create --body-file out/batch/pr_body.md
"""


@pytest.fixture
def workflows(tmp_path: Path) -> Path:
    (tmp_path / "weekly_scripts.yml").write_text(WEEKLY, encoding="utf-8")
    return tmp_path


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture edit did not apply: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_clean_fixture_passes(workflows: Path) -> None:
    assert rules.directory_problems(workflows) == []


BAD = [
    pytest.param("on:\n", "on:\n  pull_request_target:\n", "pull_request_target", id="pull-request-target"),
    pytest.param("permissions:\n  contents: read\njobs:", "permissions:\n  contents: write\njobs:",
                 "workflow permissions", id="workflow-write"),
    pytest.param("permissions:\n  contents: read\njobs:", "jobs:", "workflow permissions",
                 id="workflow-permissions-missing"),
    pytest.param("  generate:\n    runs-on: ubuntu-latest\n",
                 "  generate:\n    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n",
                 "generate: permissions", id="write-in-other-job"),
    pytest.param("  generate:\n    runs-on: ubuntu-latest\n",
                 "  generate:\n    runs-on: ubuntu-latest\n    permissions:\n",
                 "generate: permissions", id="null-permissions"),
    pytest.param("      pull-requests: write\n", "      pull-requests: write\n      actions: write\n",
                 "open-pr: permissions", id="extra-permission"),
    pytest.param("      contents: write\n      pull-requests: write\n", "      contents: write\n",
                 "open-pr: permissions", id="fewer-permissions-than-allowlisted"),
    pytest.param("    permissions:\n      contents: write\n      pull-requests: write\n",
                 "    permissions: write-all\n", "open-pr: permissions", id="write-all"),
    pytest.param(f"actions/checkout@{SHA}\n        with:", "actions/checkout@v7\n        with:",
                 "not pinned", id="unpinned-step"),
    pytest.param("  open-pr:\n",
                 "  reuse:\n    uses: someone/repo/.github/workflows/x.yml@main\n  open-pr:\n",
                 "not pinned", id="unpinned-reusable-workflow-job"),
    pytest.param("run: gh pr create", "run: gh pr create --title ${{ github.event.head_commit.message }}",
                 "expression inside run", id="expression-in-run"),
    pytest.param("GH_TOKEN: ${{ github.token }}",
                 "GH_TOKEN: ${{ github.token }}\n          KEY: ${{ secrets.GEMINI_API_KEY }}",
                 "open-pr: secret", id="allowlisted-secret-in-other-job"),
    pytest.param("${{ secrets.GEMINI_API_KEY }}", "${{ secrets.OTHER_KEY }}", "generate: secret",
                 id="other-secret"),
    pytest.param("${{ secrets.GEMINI_API_KEY }}", "${{ secrets.GITHUB_TOKEN }}", "generate: secret",
                 id="github-token-as-secret"),
    pytest.param("${{ secrets.GEMINI_API_KEY }}", "${{ toJSON(secrets) }}", "generate: secret",
                 id="all-secrets"),
    pytest.param("${{ secrets.GEMINI_API_KEY }}", "${{ secrets['GEMINI_API_KEY'] }}", "generate: secret",
                 id="secret-index-syntax"),
    pytest.param("      - name: Generate\n", "      - name: Generate\n        if: SECRETS.OTHER != ''\n",
                 "generate: secret", id="secret-in-bare-if-any-case"),
    pytest.param("    needs: generate\n", "    needs: generate\n    secrets: inherit\n",
                 "open-pr: secret", id="secrets-inherit"),
    pytest.param("permissions:\n  contents: read\njobs:",
                 "permissions:\n  contents: read\nenv:\n  KEY: ${{ secrets.GEMINI_API_KEY }}\njobs:",
                 "workflow: secret", id="secret-in-workflow-env"),
    pytest.param("run: python -m", "run: KEY=${{ secrets.GEMINI_API_KEY }} python -m", "generate run: secret",
                 id="secret-in-run"),
    pytest.param("        run: python -m", "          GH_TOKEN: ${{ github.token }}\n        run: python -m",
                 "generate: github.token", id="token-in-read-job"),
    pytest.param("        run: python -m", "          GH_TOKEN: ${{ GITHUB.TOKEN }}\n        run: python -m",
                 "generate: github.token", id="token-in-read-job-any-case"),
    pytest.param("permissions:\n  contents: read\njobs:",
                 "permissions:\n  contents: read\nenv:\n  GH_TOKEN: ${{ github.token }}\njobs:",
                 "workflow: github.token", id="token-in-workflow-env"),
    pytest.param("persist-credentials: false", "persist-credentials: true", "generate: checkout",
                 id="persisted-credentials"),
    pytest.param("persist-credentials: false", 'persist-credentials: "false"', "generate: checkout",
                 id="persist-credentials-string"),
    pytest.param("        with:\n          persist-credentials: false\n", "", "generate: checkout",
                 id="persist-credentials-default"),
]


@pytest.mark.parametrize(("old", "new", "message"), BAD)
def test_bad_workflow_fails(workflows: Path, old: str, new: str, message: str) -> None:
    edit(workflows / "weekly_scripts.yml", old, new)
    found = rules.directory_problems(workflows)
    assert any(message in problem for problem in found), found


def test_allowlist_is_per_file(workflows: Path) -> None:
    """The same jobs in a differently named file get no exceptions."""
    (workflows / "weekly_scripts.yml").rename(workflows / "other.yml")
    found = rules.directory_problems(workflows)
    for message in ("open-pr: permissions", "generate: secret", "open-pr: github.token", "open-pr: checkout"):
        assert any(message in problem for problem in found), (message, found)


def test_yaml_extension_is_read_too(workflows: Path) -> None:
    (workflows / "extra.yaml").write_text(WEEKLY.replace("contents: read", "contents: write", 1),
                                          encoding="utf-8")
    assert any(p.startswith("extra.yaml: workflow permissions") for p in rules.directory_problems(workflows))


def test_empty_directory_fails(tmp_path: Path) -> None:
    assert rules.directory_problems(tmp_path) != []


def test_assert_safe_raises_on_a_bad_workflow(workflows: Path) -> None:
    edit(workflows / "weekly_scripts.yml", "persist-credentials: false", "persist-credentials: true")
    workflow = rules.load("weekly_scripts.yml", workflows)
    with pytest.raises(AssertionError, match="generate: checkout"):
        rules.assert_safe(workflow, "weekly_scripts.yml")


def test_no_job_gets_both_a_secret_and_write_permissions() -> None:
    """The model API key never reaches a job that can push (docs/threat-model.md section 4.3)."""
    assert not set(rules.SECRET_JOBS) & set(rules.WRITE_JOBS)


def test_acceptance() -> None:
    """Every file in .github/workflows/, found by glob, passes every safety rule."""
    names = {path.name for path in rules.workflow_files()}
    assert {"ci.yml", "render.yml"} <= names
    assert rules.directory_problems(rules.WORKFLOWS) == []
