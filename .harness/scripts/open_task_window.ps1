# Opens a visible Claude Code window for one harness task (HARNESS.md section 10, Stage 0).
# Launch WITHOUT -NoExit so the window closes when the session ends:
#   cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 `
#     -Task <id> -Model claude-sonnet-5-5 -WorkDir <worktree> -Message "<brief>" [-SessionId <id to resume>]
param([string]$Task, [string]$SessionId, [string]$Model, [string]$WorkDir, [string]$Message)

$Host.UI.RawUI.WindowTitle = "Loom task: $Task"
# A clean environment: the task session must not inherit the orchestrator's identity.
Get-ChildItem env: | Where-Object { $_.Name -like 'CLAUDE*' } | ForEach-Object { Remove-Item "env:$($_.Name)" }
$env:LOOM_TASK = $Task
Set-Location $WorkDir

$resume = @()
if ($SessionId) { $resume = @('--resume', $SessionId) }
claude.cmd @resume $Message `
  --model $Model `
  --permission-mode acceptEdits `
  --disallowedTools AskUserQuestion EnterPlanMode PowerShell WebFetch WebSearch `
  --allowedTools Read Glob Grep Edit Write `
    "Bash(python -m venv:*)" "Bash(.venv/Scripts/python.exe:*)" `
    "Bash(git status:*)" "Bash(git diff:*)" "Bash(git log:*)" "Bash(git add:*)" "Bash(git commit:*)" `
    "Bash(ls:*)" "Bash(mkdir:*)"
