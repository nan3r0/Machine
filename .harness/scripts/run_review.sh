#!/bin/sh
# Runs one read-only headless review session (Gate 2 or a specialist) with a clean environment.
# No edit tools, no shell, no web. Usage: run_review.sh <prompt-file> <output-json> [role]
# The model comes from the active profile in .harness/config.yaml (TRIAL.md). Role defaults to the
# output name: <id>-sec -> security_reviewer, <id>-vq / -vqa -> visual_qa, anything else -> reviewer.
# If the profile lookup fails for any reason, the review runs on Opus, as before.
prompt_file="$1"; out="$2"; role=$(printf %s "${3:-auto}" | tr -d '\r')
here=$(dirname "$0")
model=$(python "$here/../model_for.py" "$role" --review-out "$out" 2>/dev/null | tr -d '\r') || model=""
[ -n "$model" ] || model=claude-opus-5-5
# Drop CLAUDE* and every LOOM_* variable, so a reviewer is never mistaken for the orchestrator.
unset_args=$(env | grep -oE '^(CLAUDE|LOOM_)[A-Z_]*' | sed 's/^/-u /' | tr '\n' ' ')
review() {  # <model> <output>
  # shellcheck disable=SC2086
  env $unset_args claude -p "$(cat "$prompt_file")" \
    --model "$1" \
    --output-format json \
    --allowedTools Read Grep Glob \
    --disallowedTools Edit Write MultiEdit NotebookEdit Bash PowerShell WebFetch WebSearch AskUserQuestion EnterPlanMode \
    > "$2"
}
echo "review model: $model" >&2
review "$model" "$out"
status=$?
# Trial only: re-run a sample of downgraded reviews on the baseline model, saved next to the real one
# as <name>-shadow.json. The real verdict is the one above; the shadow is only for compare_profiles.py.
shadow=$(python "$here/../model_for.py" "$role" --shadow --review-out "$out" 2>/dev/null | tr -d '\r') || shadow=""
if [ -n "$shadow" ]; then
  echo "shadow review model: $shadow" >&2
  review "$shadow" "${out%.json}-shadow.json"
fi
exit $status
