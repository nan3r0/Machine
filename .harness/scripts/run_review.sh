#!/bin/sh
# Runs one read-only headless review session (Gate 2 or a specialist) with a clean environment.
# No edit tools, no shell, no web. Usage: run_review.sh <prompt-file> <output-json>
prompt_file="$1"; out="$2"
unset_args=$(env | grep -oE '^CLAUDE[A-Z_]*' | sed 's/^/-u /' | tr '\n' ' ')
# shellcheck disable=SC2086
env $unset_args -u LOOM_TASK claude -p "$(cat "$prompt_file")" \
  --model claude-opus-5-5 \
  --output-format json \
  --allowedTools Read Grep Glob \
  --disallowedTools Edit Write MultiEdit NotebookEdit Bash PowerShell WebFetch WebSearch AskUserQuestion EnterPlanMode \
  > "$out"
