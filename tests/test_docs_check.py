"""The docs check fails when the docs drift from each other or from the repo (HARNESS.md section 10)."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests import docs_check, scope_check
from tests import workflow_rules as rules

ROOT = Path(__file__).resolve().parent.parent

LESSON_FORMAT = """\
## Entry format

### YYYY-MM-DD: short title
What happened:
Why it happened (root cause, not symptom):
Fix:
Test added: (file and name, or "none, and why")
"""

LESSON_ENTRY = """\
### 2026-11-15: A mistake
What happened: something broke.
Why it happened (root cause, not symptom): a reason.
Fix: fixed it.
Test added: none, process rule.
"""

FILES = {
    ".harness/tasks/phase1/00_a.yaml": "id: p1-a\ntests: []\n",
    ".harness/tasks/harness/01_h.yaml": "id: h-hook\n",
    ".harness/status.yaml": "done: [p1-a]\n",
    ".harness/handoffs/p1-a.md": "# Handoff: p1-a\n## Goal\nx\n## Docs\n- none\n## Evidence\n- ran\n",
    "tests/test_a.py": ("def test_acceptance() -> None:\n    pass\n\n\n"
                        "class TestB:\n    def test_b(self) -> None:\n        pass\n"),
    "workflow.md": (
        "# Build Workflow\n\n### Criterion to test map\n\n| PRD criterion | Test |\n|---|---|\n"
        "| R1.1 | `tests/test_a.py::test_acceptance` (writes `out/frames/a-*.png`) |\n"
        "| R1.2 | `tests/test_a.py::test_b` |\n| R1.3 | Manual, owner |\n\n"
        "### Phase 1 status\n\n| Task | Status | Review |\n|---|---|---|\n"
        "| Harness setup (hook) | done, 25 tests | none |\n| p1-a | done, merged | approved |\n"
        "| p1-b to p1-z | not started | |\n"
    ),
    "CLAUDE.md": ("# Project\n\n## Status\n\nDone: p1-a. Next: h-hook, then more (Kokoro-only voice).\n\n"
                  "## Commands\n\np1-ghost is not in the Status section.\n"),
    "lessons.md": (f"# Lessons\n\n{LESSON_FORMAT}\n## Traps\n\n- a trap\n\n"
                   f"## Entries\n\n{LESSON_ENTRY}\n{LESSON_ENTRY}"),
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel, text in FILES.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def edit(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture edit did not apply: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_clean_fixture_has_no_problems(repo: Path) -> None:
    assert docs_check.problems(repo) == []


def test_crlf_files_parse_the_same(repo: Path) -> None:
    for rel in ("workflow.md", "CLAUDE.md", "lessons.md", ".harness/handoffs/p1-a.md"):
        path = repo / rel
        path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    assert docs_check.problems(repo) == []


def test_done_task_without_yaml(repo: Path) -> None:
    (repo / ".harness/tasks/phase1/00_a.yaml").unlink()
    found = docs_check.problems(repo)
    assert ".harness/status.yaml: done task p1-a has no task YAML in .harness/tasks/" in found


def test_done_task_not_done_in_workflow(repo: Path) -> None:
    edit(repo, "workflow.md", "| p1-a | done, merged |", "| p1-a | in review |")
    assert docs_check.problems(repo) == [
        ".harness/status.yaml: done task p1-a is not marked done in the workflow.md Phase 1 status table"]


def test_workflow_done_task_missing_from_status(repo: Path) -> None:
    edit(repo, "workflow.md", "| p1-b to p1-z |", "| h-hook | done, merged | approved |\n| p1-b to p1-z |")
    assert docs_check.problems(repo) == [
        "workflow.md: task h-hook is marked done in the Phase 1 status table but not in .harness/status.yaml"]


def test_backticked_task_id_in_status_table_counts(repo: Path) -> None:
    edit(repo, "workflow.md", "| p1-a | done, merged |", "| `p1-a` | done, merged |")
    assert docs_check.problems(repo) == []


def test_missing_test_path(repo: Path) -> None:
    edit(repo, "workflow.md", "`tests/test_a.py::test_b`", "`tests/test_gone.py`")
    assert docs_check.problems(repo) == [
        "workflow.md: criterion-to-test map names tests/test_gone.py, which does not exist"]


def test_missing_test_function(repo: Path) -> None:
    edit(repo, "workflow.md", "::test_b`", "::nope`")
    assert docs_check.problems(repo) == [
        "workflow.md: criterion-to-test map names tests/test_a.py::nope, which has no such test function"]


def test_test_id_whose_file_is_missing(repo: Path) -> None:
    edit(repo, "workflow.md", "`tests/test_a.py::test_b`", "`tests/test_gone.py::test_b`")
    assert docs_check.problems(repo) == [
        "workflow.md: criterion-to-test map names tests/test_gone.py::test_b, which does not exist"]


def test_claude_status_names_unknown_task(repo: Path) -> None:
    edit(repo, "CLAUDE.md", "Next: h-hook", "Next: p1-ghost")
    assert docs_check.problems(repo) == [
        "CLAUDE.md: the Status section names task p1-ghost, which has no task YAML"]


def test_done_task_without_handoff(repo: Path) -> None:
    (repo / ".harness/handoffs/p1-a.md").unlink()
    assert docs_check.problems(repo) == ["done task p1-a has no handoff at .harness/handoffs/p1-a.md"]


def test_handoff_without_docs_section(repo: Path) -> None:
    edit(repo, ".harness/handoffs/p1-a.md", "## Docs\n- none\n", "")
    assert docs_check.problems(repo) == [".harness/handoffs/p1-a.md: no ## Docs section"]


def test_handoff_with_empty_docs_section(repo: Path) -> None:
    edit(repo, ".harness/handoffs/p1-a.md", "## Docs\n- none\n", "## Docs\n\n  \n")
    assert docs_check.problems(repo) == [".harness/handoffs/p1-a.md: ## Docs section is empty"]


def test_handoff_with_empty_docs_section_at_end(repo: Path) -> None:
    edit(repo, ".harness/handoffs/p1-a.md", "## Docs\n- none\n## Evidence\n- ran\n",
         "## Evidence\n- ran\n## Docs\n")
    assert docs_check.problems(repo) == [".harness/handoffs/p1-a.md: ## Docs section is empty"]


def test_lessons_entry_missing_field(repo: Path) -> None:
    edit(repo, "lessons.md", "## Entries\n\n### 2026-11-15: A mistake\nWhat happened: something broke.\n",
         "## Entries\n\n### 2026-11-15: A mistake\n")
    assert docs_check.problems(repo) == [
        "lessons.md: entry '2026-11-15: A mistake' lacks the field 'What happened'"]


def test_lessons_entry_with_empty_field(repo: Path) -> None:
    edit(repo, "lessons.md", "## Entries\n\n### 2026-11-15: A mistake\nWhat happened: something broke.\n",
         "## Entries\n\n### 2026-11-15: A mistake\nWhat happened:\n")
    assert docs_check.problems(repo) == [
        "lessons.md: entry '2026-11-15: A mistake' lacks the field 'What happened'"]


def test_lessons_fields_come_from_the_entry_format(repo: Path) -> None:
    edit(repo, "lessons.md", "Fix:\nTest added:", "Fix:\nRule going forward:\nTest added:")
    assert docs_check.problems(repo) == [
        "lessons.md: entry '2026-11-15: A mistake' lacks the field 'Rule going forward'"] * 2


def test_cli_prints_one_line_per_problem_and_fails(repo: Path) -> None:
    (repo / ".harness/handoffs/p1-a.md").unlink()
    edit(repo, "CLAUDE.md", "Next: h-hook", "Next: p1-ghost")
    result = subprocess.run([sys.executable, str(ROOT / "tests" / "docs_check.py"), str(repo)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "CLAUDE.md: the Status section names task p1-ghost, which has no task YAML",
        "done task p1-a has no handoff at .harness/handoffs/p1-a.md",
        "docs check failed: 2 problems",
    ]


def test_docs_check_runs_in_make_check_and_ci_after_scope_check() -> None:
    assert "python tests/docs_check.py" in (ROOT / "Makefile").read_text(encoding="utf-8")
    steps = rules.load("ci.yml")["jobs"]["check"]["steps"]
    names = [s.get("name") for s in steps]
    docs = names.index("Docs check")
    assert names[docs - 1] == "Scope check (task branches only)"
    assert steps[docs]["run"].strip() == "python tests/docs_check.py"


def test_docs_check_and_its_test_are_locked() -> None:
    locked = yaml.safe_load((ROOT / ".harness" / "locks.yaml").read_text(encoding="utf-8"))["locked"]
    assert scope_check.matches("tests/docs_check.py", locked)
    assert scope_check.matches("tests/test_docs_check.py", locked)


def test_acceptance() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "tests" / "docs_check.py")],
                            capture_output=True, text=True, check=False, cwd=ROOT)
    assert result.returncode == 0, result.stdout
    assert result.stdout.strip() == "docs check passed"
