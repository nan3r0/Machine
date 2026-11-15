"""R7.4: the task-aware conftest runs a task's tests only once the task is done or current."""

import shutil
from pathlib import Path

import pytest

CONFTEST = Path(__file__).with_name("conftest.py")
PASSING = "def test_ok():\n    assert True\n"


@pytest.fixture
def project(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    """A tiny project: task t-built (done) owns test_built.py, t-new (not done) owns test_new.py."""
    monkeypatch.delenv("LOOM_TASK", raising=False)
    monkeypatch.delenv("CI", raising=False)
    root = pytester.path
    tasks = root / ".harness" / "tasks" / "phase1"
    tasks.mkdir(parents=True)
    (tasks / "a.yaml").write_text("id: t-built\ntests:\n  - tests/test_built.py\n", encoding="utf-8")
    (tasks / "b.yaml").write_text("id: t-new\ntests:\n  - tests/test_new.py\n", encoding="utf-8")
    (tasks / "c.yaml").write_text("id: t-review\ntests: []\n", encoding="utf-8")
    (root / ".harness" / "status.yaml").write_text("done:\n  - t-built\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    shutil.copy(CONFTEST, tests / "conftest.py")
    for name in ("test_built.py", "test_new.py", "test_free.py"):
        (tests / name).write_text(PASSING, encoding="utf-8")
    (tests / "test_heavy.py").write_text(
        "import pytest\n\n@pytest.mark.heavy\ndef test_heavy():\n    assert True\n", encoding="utf-8")
    pytester.makeini("[pytest]\nmarkers =\n    heavy: needs ffmpeg or torch\n")
    return pytester


def test_unbuilt_task_is_skipped_with_its_id(project: pytest.Pytester) -> None:
    result = project.runpytest_subprocess("-rs")
    result.assert_outcomes(passed=2, skipped=2)
    result.stdout.fnmatch_lines(["*test_new.py*task t-new is not done*"])


def test_done_task_and_unowned_tests_run(project: pytest.Pytester) -> None:
    result = project.runpytest_subprocess("-v")
    result.stdout.fnmatch_lines(["*test_built.py::test_ok PASSED*"])
    result.stdout.fnmatch_lines(["*test_free.py::test_ok PASSED*"])


def test_current_task_runs(project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOM_TASK", "t-new")
    result = project.runpytest_subprocess("-v")
    result.stdout.fnmatch_lines(["*test_new.py::test_ok PASSED*"])


def test_task_without_tests_is_a_valid_loom_task(project: pytest.Pytester,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOM_TASK", "t-review")
    project.runpytest_subprocess().assert_outcomes(passed=2, skipped=2)


def test_unknown_loom_task_fails_loudly(project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOM_TASK", "t-typo")
    result = project.runpytest_subprocess()
    assert result.ret != 0
    result.stderr.fnmatch_lines(["*LOOM_TASK=t-typo matches no task*"])


def test_heavy_skipped_locally(project: pytest.Pytester) -> None:
    result = project.runpytest_subprocess("-rs")
    result.stdout.fnmatch_lines(["*test_heavy.py*heavy: runs only in CI*"])


def test_heavy_runs_in_ci(project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    result = project.runpytest_subprocess("-v")
    result.stdout.fnmatch_lines(["*test_heavy.py::test_heavy PASSED*"])


def test_unbuilt_heavy_test_skips_for_its_task_not_for_heaviness(project: pytest.Pytester,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    (project.path / "tests" / "test_new.py").write_text(
        "import pytest\n\n@pytest.mark.heavy\ndef test_ok():\n    assert True\n", encoding="utf-8")
    monkeypatch.setenv("CI", "true")
    result = project.runpytest_subprocess("-rs")
    result.stdout.fnmatch_lines(["*test_new.py*task t-new is not done*"])
