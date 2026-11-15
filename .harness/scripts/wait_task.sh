#!/bin/sh
# Waits until a task session has committed and rewritten its handoff, or its window was closed.
# One watcher per task: each notification costs the orchestrator a full turn.
# Usage (in the background): wait_task.sh <worktree> <task-id> <start-sha> <claude-pid>
wt="$1"; task="$2"; start="$3"; pid="$4"
handoff="$wt/.harness/handoffs/$task.md"
marker=$(mktemp)
alive() { tasklist //FI "PID eq $pid" | grep -q "$pid"; }
finished() {
  [ "$(git -C "$wt" rev-parse HEAD)" != "$start" ] && [ "$handoff" -nt "$marker" ] &&
    [ -z "$(git -C "$wt" status --porcelain --untracked-files=no)" ]
}
until { finished && sleep 120 && finished; } || ! alive; do sleep 30; done
if finished; then echo "TASK_DONE $(git -C "$wt" rev-parse --short HEAD)"; else echo "WINDOW_CLOSED"; fi
