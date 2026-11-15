"""The CI scope check enforces the same rules as the lock hook, server side."""

import ast
import subprocess
from pathlib import Path

import pytest

from tests import scope_check

IMPLEMENTER = {"id": "p1-captions-ass", "role": "implementer",
               "paths_allowed": ["pipeline/render/captions_ass.py", "assets/fonts/**"]}
TEST_AUTHOR = {"id": "p1-contracts", "role": "test_author",
               "paths_allowed": ["tests/**", ".harness/locks.yaml"]}
LOCKED = ["tests/**", "pipeline/schema.py"]


@pytest.mark.parametrize("path", [
    "pipeline/render/captions_ass.py", "assets/fonts/Montserrat.ttf", ".harness/handoffs/p1-captions-ass.md",
    "CONTRACT_CHANGE.md", "ENV_ISSUE.md"])
def test_in_scope_paths_pass(path: str) -> None:
    assert scope_check.violations(IMPLEMENTER, LOCKED, [path]) == []


@pytest.mark.parametrize("path", [
    "pipeline/render/compose.py", "README.md", ".harness/handoffs/p1-compose.md", ".github/workflows/ci.yml"])
def test_out_of_scope_paths_fail(path: str) -> None:
    assert scope_check.violations(IMPLEMENTER, LOCKED, [path]) == [
        f"{path}: outside paths_allowed for p1-captions-ass"]


@pytest.mark.parametrize("path", ["tests/render/test_captions_ass.py", "pipeline/schema.py"])
def test_locked_paths_fail_for_implementers(path: str) -> None:
    task = dict(IMPLEMENTER, paths_allowed=["**"])
    assert scope_check.violations(task, LOCKED, [path]) == [f"{path}: locked in .harness/locks.yaml"]


@pytest.mark.parametrize("path", [".harness/status.yaml", ".harness/tasks/phase1/05_captions_ass.yaml"])
def test_harness_files_fail_for_implementers(path: str) -> None:
    task = dict(IMPLEMENTER, paths_allowed=["**"])
    assert scope_check.violations(task, [], [path]) == [f"{path}: harness file, implementers never edit it"]


def test_contract_owner_may_change_locked_paths_in_scope() -> None:
    assert scope_check.violations(TEST_AUTHOR, LOCKED, ["tests/conftest.py", ".harness/locks.yaml"]) == []


@pytest.mark.parametrize("path", [
    ".claude/hooks/enforce_locks.py", ".claude/settings.json", ".claude/settings.local.json",
    ".claude/agents/reviewer.md", ".claude/commands/go.md", ".claude/skills/x/SKILL.md",
    ".claude/plugins/p.json", ".claude.json", ".mcp.json", "managed-settings.json",
    "sub/dir/.claude/hooks/x.py", "tests/fixtures/.mcp.json"])
def test_admin_files_fail_even_for_contract_owner(path: str) -> None:
    task = dict(TEST_AUTHOR, paths_allowed=["**"])
    assert scope_check.violations(task, [], [path]) == [f"{path}: Claude Code admin file, owner-only"]


def test_admin_paths_match_the_hook() -> None:
    hook = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "enforce_locks.py"
    tree = ast.parse(hook.read_text(encoding="utf-8"))
    assigned = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "ADMIN_PATHS" for t in node.targets))
    assert ast.literal_eval(assigned) == scope_check.ADMIN_PATHS


def test_case_is_ignored_like_the_hook() -> None:
    assert scope_check.violations(IMPLEMENTER, LOCKED, ["Tests/Render/X.py"]) == [
        "Tests/Render/X.py: locked in .harness/locks.yaml"]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo whose main branch holds one task and locks, with a task branch checked out."""
    (tmp_path / ".harness" / "tasks" / "phase1").mkdir(parents=True)
    (tmp_path / ".harness" / "tasks" / "phase1" / "05.yaml").write_text(
        "id: p1-captions-ass\nrole: implementer\npaths_allowed:\n  - pipeline/render/captions_ass.py\n",
        encoding="utf-8")
    (tmp_path / ".harness" / "locks.yaml").write_text("locked:\n  - tests/**\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "task/p1-captions-ass")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def commit(repo: Path, path: str, text: str = "change\n") -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"edit {path}")


def test_branch_in_scope_passes(repo: Path) -> None:
    commit(repo, "pipeline/render/captions_ass.py")
    assert scope_check.main(["task/p1-captions-ass", "main"]) == 0


def test_branch_editing_locked_test_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, "pipeline/render/captions_ass.py")
    commit(repo, "tests/test_x.py", "x = 2\n")
    assert scope_check.main(["task/p1-captions-ass", "main"]) == 1
    assert "tests/test_x.py: locked" in capsys.readouterr().out


def test_rename_out_of_locked_path_is_caught(repo: Path) -> None:
    (repo / "pipeline" / "render").mkdir(parents=True)
    git(repo, "mv", "tests/test_x.py", "pipeline/render/captions_ass.py")
    git(repo, "commit", "-q", "-m", "move")
    assert scope_check.main(["task/p1-captions-ass", "main"]) == 1


def test_branch_cannot_widen_its_own_scope(repo: Path) -> None:
    task = ".harness/tasks/phase1/05.yaml"
    commit(repo, task, "id: p1-captions-ass\nrole: test_author\npaths_allowed:\n  - '**'\n")
    commit(repo, "README.md")
    assert scope_check.main(["task/p1-captions-ass", "main"]) == 1


def test_unknown_task_fails(repo: Path) -> None:
    assert scope_check.main(["task/p1-nope", "main"]) == 1


def test_bad_task_id_fails(repo: Path) -> None:
    assert scope_check.main(["task/../../etc", "main"]) == 1


@pytest.mark.parametrize("branch", ["Task/p1-captions-ass", "TASK/p1-captions-ass"])
def test_task_prefix_in_other_case_fails_even_in_scope(repo: Path, branch: str) -> None:
    """CI would not set LOOM_TASK for this branch, so the task's tests would silently skip."""
    commit(repo, "pipeline/render/captions_ass.py")
    assert scope_check.main([branch, "main"]) == 1


def test_non_task_branch_is_skipped(repo: Path) -> None:
    assert scope_check.main(["main", "main"]) == 0
