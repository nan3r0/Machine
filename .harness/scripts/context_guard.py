"""Stop hook: rotate a session into a fresh window when its context passes the threshold.

HARNESS.md section 7a. Plain Python, no model. Exit 0 lets the session stop; exit 2 blocks the
stop and feeds stderr back to the session. Any problem reading input exits 0: a broken guard
must never block a session.
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
    """Return (tokens in use, model) of the last assistant message, or None if unreadable."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            message = json.loads(line).get("message")
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


def main(stdin_text):
    try:
        payload = json.loads(stdin_text)
        if payload.get("stop_hook_active"):
            return 0
        session_id = str(payload["session_id"])
        usage = last_usage(payload["transcript_path"])
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        config = (project / ".harness" / "config.yaml").read_text(encoding="utf-8")
        rotation = yaml.safe_load(config)["rotation"]
    except (ValueError, KeyError, TypeError, AttributeError, OSError, yaml.YAMLError):
        return 0
    if usage is None:
        return 0

    tokens, model = usage
    task = os.environ.get("LOOM_TASK")
    threshold = rotation["rotate_context_pct" if task else "orchestrator_rotate_context_pct"]
    pct = int(tokens * 100 / rotation["context_window_tokens"])
    if pct < threshold:
        return 0

    name = task or ORCHESTRATOR
    handoff = project / ".harness" / "handoffs" / f"{name}.md"
    rotate_dir = project / ".harness" / "rotate"
    started = rotate_dir / f"{session_id}.started"
    launched = rotate_dir / f"{session_id}.launched"
    if launched.exists():
        return 0
    if not started.exists() or not handoff.exists() or handoff.stat().st_mtime <= started.stat().st_mtime:
        rotate_dir.mkdir(parents=True, exist_ok=True)
        started.touch(exist_ok=True)
        print(BLOCK_MESSAGE.format(pct=pct), file=sys.stderr)
        return 2

    try:
        launch_window(
            task=name,
            model=model,
            workdir=str(project),
            message=TASK_MESSAGE if task else ORCHESTRATOR_MESSAGE,
            close_pid=os.environ.get("LOOM_WINDOW_PID"),
        )
    except OSError as error:
        print(f"context_guard: could not open the replacement window: {error}", file=sys.stderr)
        return 0
    launched.touch()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
