"""Pipe-tests for .claude/hooks/enforce_locks.py.

Each test builds a throwaway project, feeds the hook a PreToolUse payload on
stdin and checks the exit code: 0 allows the edit, 2 blocks it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "enforce_locks.py"

TASK_YAML = """\
id: p1-captions
title: test task
depends_on: []
role: implementer
paths_allowed:
  - pipeline/render/captions_ass.py
  - assets/fonts/**
tests: [tests/render/test_captions_ass.py]
"""

CONTRACTS_YAML = """\
id: p1-contracts
title: contracts
depends_on: []
role: test_author
paths_allowed:
  - tests/**
  - .harness/locks.yaml
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    tasks = tmp_path / ".harness" / "tasks" / "phase1"
    tasks.mkdir(parents=True)
    (tasks / "captions.yaml").write_text(TASK_YAML, encoding="utf-8")
    (tasks / "contracts.yaml").write_text(CONTRACTS_YAML, encoding="utf-8")
    (tmp_path / ".harness" / "locks.yaml").write_text(
        "locked:\n  - tests/**\n  - pipeline/schema.py\n", encoding="utf-8"
    )
    return tmp_path


def run_hook(root: Path, file_path: str, task: str | None = None,
             tool: str = "Write", key: str = "file_path",
             pythonpath: Path | None = None, admin: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("LOOM_TASK", "LOOM_ADMIN")}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    if admin:
        env["LOOM_ADMIN"] = "1"
    if pythonpath:
        env["PYTHONPATH"] = str(pythonpath)
    if task:
        env["LOOM_TASK"] = task
    payload = {"tool_name": tool, "tool_input": {key: file_path}, "cwd": str(root)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env)


def test_no_task_allows_unlocked_file(project: Path) -> None:
    assert run_hook(project, str(project / "pipeline" / "x.py")).returncode == 0


def test_no_task_blocks_locked_file(project: Path) -> None:
    result = run_hook(project, str(project / "tests" / "render" / "test_a.py"))
    assert result.returncode == 2
    assert "locked" in result.stderr


def test_relative_path_is_resolved_against_project(project: Path) -> None:
    assert run_hook(project, "pipeline/schema.py").returncode == 2


def test_windows_backslashes_and_case_are_normalised(project: Path) -> None:
    path = str(project).replace("/", "\\") + "\\PIPELINE\\Schema.py"
    assert run_hook(project, path).returncode == 2


def test_dotdot_cannot_escape_lock(project: Path) -> None:
    assert run_hook(project, "pipeline/../tests/x.py").returncode == 2


def test_empty_locks_file_allows_everything(project: Path) -> None:
    (project / ".harness" / "locks.yaml").write_text("", encoding="utf-8")
    assert run_hook(project, "tests/x.py").returncode == 0


def with_extra_allowed(pattern: str) -> str:
    """Task YAML with one more paths_allowed entry, still valid YAML."""
    return TASK_YAML.replace("  - assets/fonts/**\n", f"  - assets/fonts/**\n  - {pattern}\n")


def test_extra_allowed_yaml_is_valid() -> None:
    task = yaml.safe_load(with_extra_allowed("'**'"))
    assert task["paths_allowed"][-1] == "**"


def test_task_allows_path_in_paths_allowed(project: Path) -> None:
    assert run_hook(project, "pipeline/render/captions_ass.py", "p1-captions").returncode == 0


def test_task_allows_double_star_glob(project: Path) -> None:
    assert run_hook(project, "assets/fonts/inter/Inter.ttf", "p1-captions").returncode == 0


def test_task_blocks_path_outside_paths_allowed(project: Path) -> None:
    result = run_hook(project, "pipeline/render/compose.py", "p1-captions")
    assert result.returncode == 2
    assert "paths_allowed" in result.stderr


def test_task_blocks_path_outside_project(project: Path) -> None:
    outside = str(project.parent / "elsewhere.py")
    assert run_hook(project, outside, "p1-captions").returncode == 2


def test_task_always_allows_own_handoff_and_contract_change(project: Path) -> None:
    assert run_hook(project, ".harness/handoffs/p1-captions.md", "p1-captions").returncode == 0
    assert run_hook(project, "CONTRACT_CHANGE.md", "p1-captions").returncode == 0
    assert run_hook(project, "ENV_ISSUE.md", "p1-captions").returncode == 0


def test_task_blocks_other_tasks_handoff(project: Path) -> None:
    assert run_hook(project, ".harness/handoffs/p1-other.md", "p1-captions").returncode == 2


def test_implementer_blocked_from_harness_files_even_if_allowed(project: Path) -> None:
    yaml_path = project / ".harness" / "tasks" / "phase1" / "captions.yaml"
    yaml_path.write_text(with_extra_allowed("'**'"), encoding="utf-8")
    for path in (".harness/locks.yaml", ".harness/status.yaml", ".harness/tasks/phase1/captions.yaml",
                 ".claude/settings.json", ".claude/hooks/enforce_locks.py"):
        assert run_hook(project, path, "p1-captions").returncode == 2, path


def test_implementer_blocked_from_lock_even_if_allowed(project: Path) -> None:
    yaml_path = project / ".harness" / "tasks" / "phase1" / "captions.yaml"
    yaml_path.write_text(with_extra_allowed("tests/**"), encoding="utf-8")
    assert run_hook(project, "tests/render/test_captions_ass.py", "p1-captions").returncode == 2


def test_test_author_may_edit_locked_tests_and_locks(project: Path) -> None:
    assert run_hook(project, "tests/render/test_a.py", "p1-contracts").returncode == 0
    assert run_hook(project, ".harness/locks.yaml", "p1-contracts").returncode == 0


def test_unknown_task_fails_closed(project: Path) -> None:
    result = run_hook(project, "pipeline/render/captions_ass.py", "p1-nope")
    assert result.returncode == 2
    assert "p1-nope" in result.stderr


def test_broken_task_yaml_fails_closed(project: Path) -> None:
    yaml_path = project / ".harness" / "tasks" / "phase1" / "captions.yaml"
    yaml_path.write_text("id: [unclosed\n", encoding="utf-8")
    assert run_hook(project, "pipeline/render/captions_ass.py", "p1-captions").returncode == 2


ADMIN_FILES = (".claude/hooks/enforce_locks.py", ".claude/settings.json",
               ".claude/settings.local.json", ".claude/agents/implementer.md")


def test_admin_files_blocked_without_task(project: Path) -> None:
    for path in ADMIN_FILES:
        result = run_hook(project, path)
        assert result.returncode == 2, path
        assert "LOOM_ADMIN" in result.stderr


def test_admin_files_blocked_even_for_contract_owner_task(project: Path) -> None:
    contracts = project / ".harness" / "tasks" / "phase1" / "contracts.yaml"
    contracts.write_text(CONTRACTS_YAML + "  - '**'\n", encoding="utf-8")  # paths_allowed is the last key
    for path in ADMIN_FILES:
        result = run_hook(project, path, "p1-contracts")
        assert result.returncode == 2, path
        assert "LOOM_ADMIN" in result.stderr


def test_admin_env_allows_admin_files_without_task(project: Path) -> None:
    for path in ADMIN_FILES:
        assert run_hook(project, path, admin=True).returncode == 0, path


@pytest.mark.parametrize("path", [
    "TESTS~1/x.py",            # 8.3 short name for tests/
    "tests./x.py",             # Windows strips the trailing dot
    "tests /x.py",             # and the trailing space
    "pipeline/schema.py:alt",  # alternate data stream
])
def test_windows_path_tricks_are_blocked(project: Path, path: str) -> None:
    result = run_hook(project, path)
    assert result.returncode == 2
    assert "path" in result.stderr


def test_admin_files_outside_project_blocked_without_task(project: Path) -> None:
    for path in (project.parent / "home" / ".claude" / "settings.json",
                 project.parent / "parent-repo" / ".claude" / "hooks" / "x.py",
                 project / "nested" / ".claude" / "agents" / "implementer.md"):
        result = run_hook(project, str(path))
        assert result.returncode == 2, path
        assert "LOOM_ADMIN" in result.stderr


def test_admin_env_allows_admin_file_outside_project(project: Path) -> None:
    path = project.parent / "home" / ".claude" / "settings.json"
    assert run_hook(project, str(path), admin=True).returncode == 0


def test_plain_file_outside_project_allowed_without_task(project: Path) -> None:
    """Planning sessions still write Claude's memory files outside the repo."""
    path = project.parent / "home" / ".claude" / "projects" / "memory" / "note.md"
    assert run_hook(project, str(path)).returncode == 0


@pytest.mark.parametrize("prefix", ["\\\\?\\", "\\\\.\\", "//?/", "//./"])
def test_device_path_prefixes_are_blocked(project: Path, prefix: str) -> None:
    result = run_hook(project, prefix + str(project / "tests" / "x.py"))
    assert result.returncode == 2
    assert "path" in result.stderr


def test_symlink_into_locked_dir_is_blocked(project: Path) -> None:
    (project / "tests").mkdir()
    try:
        os.symlink(project / "tests", project / "alias", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need extra privileges on this machine")
    assert run_hook(project, "alias/x.py").returncode == 2


def test_missing_pyyaml_fails_closed(project: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    fake = tmp_path_factory.mktemp("fake_site")
    (fake / "yaml.py").write_text("raise ImportError('no PyYAML')\n", encoding="utf-8")
    result = run_hook(project, "pipeline/x.py", pythonpath=fake)
    assert result.returncode == 2
    assert "ImportError" in result.stderr


def test_notebook_edit_uses_notebook_path(project: Path) -> None:
    result = run_hook(project, "tests/a.ipynb", tool="NotebookEdit", key="notebook_path")
    assert result.returncode == 2


def test_non_edit_tool_passes_through(project: Path) -> None:
    assert run_hook(project, "tests/x.py", "p1-captions", tool="Read").returncode == 0
