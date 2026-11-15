# Opens a visible Claude Code window for one harness task (HARNESS.md section 10, Stage 0).
# Launch WITHOUT -NoExit so the window closes when the session ends:
#   cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 `
#     -Task <id> -Model claude-sonnet-5-5 -WorkDir <worktree> -Message "<brief>" [-SessionId <id to resume>]
# -Task orchestrator opens the orchestrator (no LOOM_TASK). -ClosePid <pid> stops that old window's
# PowerShell once the new claude process has started (used by .harness/scripts/context_guard.py).
param([string]$Task, [string]$SessionId, [string]$Model, [string]$WorkDir, [string]$Message, [int]$ClosePid)

$isOrchestrator = $Task -eq 'orchestrator'
$Host.UI.RawUI.WindowTitle = if ($isOrchestrator) { 'Loom orchestrator' } else { "Loom task: $Task" }
# A clean environment: the task session must not inherit the orchestrator's identity.
Get-ChildItem env: | Where-Object { $_.Name -like 'CLAUDE*' -or $_.Name -like 'LOOM_*' } | ForEach-Object { Remove-Item "env:$($_.Name)" }
if (-not $isOrchestrator) { $env:LOOM_TASK = $Task }
# Lets the context guard hook name this window when it rotates the session.
$env:LOOM_WINDOW_PID = $PID
Set-Location $WorkDir

$resume = @()
if ($SessionId) { $resume = @('--resume', $SessionId) }

if ($ClosePid) {
  # Once claude.cmd has started (this window has a child process), close the old window.
  Start-Job -ScriptBlock {
    param($pidToClose, $me)
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
      if (Get-CimInstance Win32_Process -Filter "ParentProcessId=$me") { break }
      Start-Sleep -Milliseconds 500
    }
    Stop-Process -Id $pidToClose -Force -ErrorAction SilentlyContinue
  } -ArgumentList $ClosePid, $PID | Out-Null
}

claude.cmd @resume $Message `
  --model $Model `
  --permission-mode acceptEdits `
  --disallowedTools AskUserQuestion EnterPlanMode PowerShell WebFetch WebSearch `
  --allowedTools Read Glob Grep Edit Write `
    "Bash(python -m venv:*)" `
    "Bash(.venv/Scripts/python.exe -m pytest:*)" "Bash(.venv/Scripts/python.exe -m ruff:*)" `
    "Bash(.venv/Scripts/python.exe -m mypy:*)" "Bash(.venv/Scripts/python.exe -m pip install -r:*)" `
    "Bash(git status:*)" "Bash(git diff:*)" "Bash(git log:*)" "Bash(git add:*)" "Bash(git commit:*)" `
    "Bash(ls:*)" "Bash(mkdir:*)"
