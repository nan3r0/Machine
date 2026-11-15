"""Tests for .harness/scripts/context_guard.py (Stop hook that rotates sessions at the context threshold).

Each test builds a throwaway project and calls the hook's main() with a Stop payload.
The window launcher is monkeypatched, so nothing is ever started.
"""

import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / "scripts" / "context_guard.py"

CONFIG = """\
rotation:
  rotate_context_pct: 60
  orchestrator_rotate_context_pct: 50
  context_window_tokens: 1000
"""


@pytest.fixture
def guard():
    spec = importlib.util.spec_from_file_location("context_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / ".harness" / "handoffs").mkdir(parents=True)
    (tmp_path / ".harness" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("LOOM_TASK", raising=False)
    monkeypatch.delenv("LOOM_WINDOW_PID", raising=False)
    monkeypatch.delenv("LOOM_ROLE", raising=False)
    return tmp_path


@pytest.fixture
def launches(guard, monkeypatch):
    calls = []
    monkeypatch.setattr(guard, "launch_window", lambda **kwargs: calls.append(kwargs))
    return calls


def write_transcript(project, tokens, model="claude-sonnet-5-5"):
    """Split tokens over the three usage fields the guard must sum."""
    usage = {
        "input_tokens": 1,
        "cache_read_input_tokens": tokens - 11,
        "cache_creation_input_tokens": 10,
        "output_tokens": 999999,
    }
    lines = [
        {"type": "assistant", "message": {"model": model, "usage": {"input_tokens": 1}}},
        {"type": "assistant", "message": {"model": model, "usage": usage}},
        {"type": "user", "message": {"content": "hi"}},
    ]
    path = project / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def run(guard, transcript, active=False, session="s1"):
    payload = {"transcript_path": str(transcript), "stop_hook_active": active, "session_id": session}
    return guard.main(json.dumps(payload))


def test_below_threshold_passes(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    assert run(guard, write_transcript(project, 590)) == 0
    assert launches == []


def test_first_crossing_blocks_with_message(guard, project, launches, capsys, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    assert run(guard, write_transcript(project, 600)) == 2
    err = capsys.readouterr().err
    assert "Context at 60%." in err
    assert "reply ROTATE" in err
    assert (project / ".harness" / "rotate" / "s1.started").exists()
    assert launches == []


def test_started_marker_keeps_first_block_time(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    transcript = write_transcript(project, 700)
    assert run(guard, transcript) == 2
    marker = project / ".harness" / "rotate" / "s1.started"
    first = time.time() - 100
    os.utime(marker, (first, first))
    assert run(guard, transcript) == 2
    assert marker.stat().st_mtime == pytest.approx(first, abs=1)


def test_stale_handoff_still_blocks(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    handoff = project / ".harness" / "handoffs" / "t1.md"
    handoff.write_text("old", encoding="utf-8")
    old = time.time() - 100
    os.utime(handoff, (old, old))
    assert run(guard, write_transcript(project, 700)) == 2
    assert launches == []


def test_fresh_handoff_launches_task_once(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    monkeypatch.setenv("LOOM_WINDOW_PID", "4242")
    transcript = write_transcript(project, 700)
    assert run(guard, transcript) == 2
    marker = project / ".harness" / "rotate" / "s1.started"
    later = marker.stat().st_mtime + 5
    handoff = project / ".harness" / "handoffs" / "t1.md"
    handoff.write_text("new", encoding="utf-8")
    os.utime(handoff, (later, later))
    assert run(guard, transcript, active=True) == 0
    assert launches == [
        {
            "task": "t1",
            "model": "claude-sonnet-5-5",
            "workdir": str(project),
            "message": "Read your handoff and continue the task",
            "close_pid": "4242",
        }
    ]
    assert run(guard, transcript, active=True) == 0
    assert len(launches) == 1


def test_orchestrator_uses_lower_threshold_and_own_handoff(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_ROLE", "orchestrator")
    transcript = write_transcript(project, 500)
    assert run(guard, transcript) == 2
    marker = project / ".harness" / "rotate" / "s1.started"
    later = marker.stat().st_mtime + 5
    handoff = project / ".harness" / "handoffs" / "orchestrator.md"
    handoff.write_text("new", encoding="utf-8")
    os.utime(handoff, (later, later))
    assert run(guard, transcript, active=True) == 0
    assert launches[0]["task"] == "orchestrator"
    assert launches[0]["message"] == "continue as orchestrator"
    assert launches[0]["close_pid"] is None


def test_task_session_at_50_percent_passes(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    assert run(guard, write_transcript(project, 500)) == 0


@pytest.mark.parametrize("content", ["", "not json\n{bad", '{"type": "assistant", "message": {}}'])
def test_malformed_transcript_exits_zero(guard, project, launches, content):
    transcript = project / "bad.jsonl"
    transcript.write_text(content, encoding="utf-8")
    assert run(guard, transcript, active=True) == 0
    assert launches == []


def test_missing_transcript_and_bad_payload_exit_zero(guard, project, launches):
    assert run(guard, project / "nope.jsonl") == 0
    assert guard.main("not json") == 0


def test_launch_failure_does_not_block(guard, project, monkeypatch, capsys):
    def boom(**kwargs):
        raise OSError("no powershell")

    monkeypatch.setattr(guard, "launch_window", boom)
    monkeypatch.setenv("LOOM_ROLE", "orchestrator")
    transcript = write_transcript(project, 700)
    run(guard, transcript)
    marker = project / ".harness" / "rotate" / "s1.started"
    later = marker.stat().st_mtime + 5
    handoff = project / ".harness" / "handoffs" / "orchestrator.md"
    handoff.write_text("new", encoding="utf-8")
    os.utime(handoff, (later, later))
    assert run(guard, transcript, active=True) == 0
    assert "no powershell" in capsys.readouterr().err


def test_acceptance(guard, project, launches, monkeypatch):
    """Cross the threshold, write the handoff, and the replacement session launches."""
    monkeypatch.setenv("LOOM_TASK", "t1")
    transcript = write_transcript(project, 650)
    assert run(guard, transcript) == 2
    marker = project / ".harness" / "rotate" / "s1.started"
    later = marker.stat().st_mtime + 5
    handoff = project / ".harness" / "handoffs" / "t1.md"
    handoff.write_text("done", encoding="utf-8")
    os.utime(handoff, (later, later))
    assert run(guard, transcript, active=True) == 0
    assert [call["task"] for call in launches] == ["t1"]


def test_unmarked_session_is_never_guarded(guard, project, launches):
    assert run(guard, write_transcript(project, 900)) == 0
    assert not (project / ".harness" / "rotate").exists()


def test_stop_hook_active_does_not_block_again(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    assert run(guard, write_transcript(project, 900), active=True) == 0
    assert not (project / ".harness" / "rotate").exists()


def test_missing_model_falls_back_to_config(guard, project, launches, monkeypatch):
    (project / ".harness" / "config.yaml").write_text(
        CONFIG + "roles:\n  implementer: claude-sonnet-5-5\n  orchestrator: claude-sonnet-5-5\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOOM_TASK", "t1")
    transcript = write_transcript(project, 700, model="<synthetic>")
    assert run(guard, transcript) == 2
    marker = project / ".harness" / "rotate" / "s1.started"
    handoff = project / ".harness" / "handoffs" / "t1.md"
    handoff.write_text("new", encoding="utf-8")
    os.utime(handoff, (marker.stat().st_mtime + 5,) * 2)
    assert run(guard, transcript, active=True) == 0
    assert launches[0]["model"] == "claude-sonnet-5-5"


def test_bad_config_exits_zero(guard, project, launches, monkeypatch, capsys):
    (project / ".harness" / "config.yaml").write_text("rotation:\n", encoding="utf-8")
    monkeypatch.setenv("LOOM_TASK", "t1")
    assert run(guard, write_transcript(project, 900)) == 0
    assert "context_guard: skipped" in capsys.readouterr().err


def test_sidechain_usage_is_ignored(guard, project, launches, monkeypatch):
    monkeypatch.setenv("LOOM_TASK", "t1")
    transcript = write_transcript(project, 100)
    side = {"isSidechain": True, "message": {"model": "m", "usage": {"input_tokens": 900}}}
    with transcript.open("a", encoding="utf-8") as handle:
        handle.write("\n" + json.dumps(side))
    assert run(guard, transcript) == 0
