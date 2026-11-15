import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "log_outcome.py"


def test_appends_one_record_with_model_from_config(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "config.yaml").write_text(
        "roles:\n  implementer: claude-sonnet-5-5\n", encoding="utf-8")
    args = [sys.executable, str(SCRIPT), "p1-align", "--attempt", "2", "--result", "tests_failed",
            "--failing", "test_a", "test_b", "--turns", "23", "--duration", "412"]
    for _ in range(2):
        subprocess.run(args, cwd=tmp_path, check=True)

    lines = (tmp_path / ".harness" / "log" / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["task_id"] == "p1-align"
    assert record["model"] == "claude-sonnet-5-5"
    assert record["role"] == "implementer"
    assert record["failing_tests"] == ["test_a", "test_b"]
    assert record["attempt"] == 2 and record["turns"] == 23 and record["duration_s"] == 412
    assert record["failure_category"] is None
    assert record["rotation_reason"] is None and record["auto_compacted"] is False
    assert record["handoff_quality"] == "agent"


def test_records_rotation_fields(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "config.yaml").write_text(
        "roles:\n  implementer: claude-sonnet-5-5\n", encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT), "p1-qa", "--result", "rotated",
                    "--rotation-reason", "context_limit", "--context-pct", "55",
                    "--handoff-quality", "fallback", "--auto-compacted"], cwd=tmp_path, check=True)
    record = json.loads((tmp_path / ".harness" / "log" / "outcomes.jsonl").read_text(encoding="utf-8"))
    assert record["rotation_reason"] == "context_limit"
    assert record["context_pct"] == 55
    assert record["handoff_quality"] == "fallback"
    assert record["auto_compacted"] is True


def test_accepts_usage_limit_result(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "config.yaml").write_text(
        "roles:\n  implementer: claude-sonnet-5-5\n", encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT), "p1-qa", "--result", "usage_limit"],
                   cwd=tmp_path, check=True)


def test_rejects_unknown_result(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(SCRIPT), "p1-x", "--result", "meh"],
                            cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
