"""Stop hook: rotate a session into a fresh window when its context passes the threshold.

HARNESS.md section 7a. Plain Python, no model. Exit 0 lets the session stop; exit 2 blocks the
stop and feeds stderr back to the session. Any problem reading input or config exits 0 with a
stderr line: a broken guard must never block a session. Only sessions that identify themselves
(LOOM_TASK for a task, LOOM_ROLE=orchestrator for the orchestrator) are guarded.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

USAGE_FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
BLOCK_MESSAGE = (
    "Context at {pct}%. Update your handoff (status partial if unfinished) and the docs it lists, "
    "commit, then reply ROTATE."
)
TASK_MESSAGE = "Read your handoff and continue the task"
ORCHESTRATOR_MESSAGE = "continue as orchestrator"
ORCHESTRATOR = "orchestrator"


def last_usage(transcript_path):
    """Return (tokens in use, model) of the last main-thread assistant message, or None if unreadable."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            entry = json.loads(line)
            if entry.get("isSidechain"):
                continue
            message = entry["message"]
            usage = message["usage"]
            tokens = sum(int(usage.get(field, 0)) for field in USAGE_FIELDS)
            return tokens, message.get("model")
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
    return None


def launch_window(task, model, workdir, message, close_pid):
    script = Path(workdir) / ".harness" / "scripts" / "open_task_window.ps1"
    title = "Loom orchestrator" if task == ORCHESTRATOR else f"Loom task: {task}"
    command = [
        "cmd", "/c", "start", title, "powershell.exe", "-ExecutionPolicy", "Bypass",
        "-File", str(script), "-Task", task, "-Model", model, "-WorkDir", str(workdir),
        "-Message", message,
    ]
    if close_pid:
        command += ["-ClosePid", str(close_pid)]
    subprocess.Popen(command)


def session_name():
    """Task id, "orchestrator", or None for a session the harness did not start."""
    task = os.environ.get("LOOM_TASK")
    if task:
        return task
    if os.environ.get("LOOM_ROLE") == ORCHESTRATOR:
        return ORCHESTRATOR
    return None


def usable_model(model, config, name):
    """The session's own model, or the configured role model when the transcript has none."""
    if model and not model.startswith("<"):
        return model
    return config["roles"]["orchestrator" if name == ORCHESTRATOR else "implementer"]


def percent_used(tokens, rotation):
    return int(tokens * 100 / rotation["context_window_tokens"])


def rotate(name, model, project, session_id, active, pct_used):
    """Block the first crossing; launch the replacement once the handoff is fresh. Returns the exit code."""
    handoff = project / ".harness" / "handoffs" / f"{name}.md"
    rotate_dir = project / ".harness" / "rotate"
    started = rotate_dir / f"{session_id}.started"
    launched = rotate_dir / f"{session_id}.launched"
    if launched.exists():
        return 0
    # Claude Code sets stop_hook_active on the stop that follows our block, which is exactly the
    # stop where the launch has to happen. It only suppresses a second block.
    fresh = started.exists() and handoff.exists() and handoff.stat().st_mtime > started.stat().st_mtime
    if fresh:
        try:
            launch_window(
                task=name,
                model=model,
                workdir=str(project),
                message=ORCHESTRATOR_MESSAGE if name == ORCHESTRATOR else TASK_MESSAGE,
                close_pid=os.environ.get("LOOM_WINDOW_PID"),
            )
        except OSError as error:
            print(f"context_guard: could not open the replacement window: {error}", file=sys.stderr)
            return 0
        launched.touch()
        return 0
    if active or pct_used is None:
        return 0
    rotate_dir.mkdir(parents=True, exist_ok=True)
    started.touch()
    print(BLOCK_MESSAGE.format(pct=pct_used), file=sys.stderr)
    return 2


def main(stdin_text):
    name = session_name()
    if name is None:
        return 0
    try:
        payload = json.loads(stdin_text)
        session_id = str(payload["session_id"])
        usage = last_usage(payload["transcript_path"])
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        config = yaml.safe_load((project / ".harness" / "config.yaml").read_text(encoding="utf-8"))
        rotation = config["rotation"]
        if usage is None:
            return 0
        tokens, model = usage
        key = "orchestrator_rotate_context_pct" if name == ORCHESTRATOR else "rotate_context_pct"
        crossed = percent_used(tokens, rotation) >= rotation[key]
        pct = percent_used(tokens, rotation) if crossed else None
        # A fresh handoff launches even when the context reading is stale or below the threshold.
        return rotate(name, usable_model(model, config, name), project, session_id,
                      bool(payload.get("stop_hook_active")), pct)
    except (LookupError, ValueError, TypeError, AttributeError, OSError, ArithmeticError,
            yaml.YAMLError) as error:
        print(f"context_guard: skipped, {type(error).__name__}: {error}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
