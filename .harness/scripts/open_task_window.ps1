# Opens a visible Claude Code window for one harness task (HARNESS.md section 10, Stage 0).
# Launch WITHOUT -NoExit so the window closes when the session ends:
#   cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 `
#     -Task <id> -Model claude-sonnet-5-5 -WorkDir <worktree> -Message "<brief>" [-SessionId <id to resume>]
# -Task orchestrator opens the orchestrator (no LOOM_TASK). -ClosePid <pid> stops that old window's
# PowerShell once the new claude process has started (used by .claude/hooks/context_guard.py).
param([string]$Task, [string]$SessionId, [string]$Model, [string]$WorkDir, [string]$Message, [int]$ClosePid)

$isOrchestrator = $Task -eq 'orchestrator'
$Host.UI.RawUI.WindowTitle = if ($isOrchestrator) { 'Loom orchestrator' } else { "Loom task: $Task" }
# A clean environment: the task session must not inherit the orchestrator's identity.
Get-ChildItem env: | Where-Object { $_.Name -like 'CLAUDE*' -or $_.Name -like 'LOOM_*' } | ForEach-Object { Remove-Item "env:$($_.Name)" }
if ($isOrchestrator) { $env:LOOM_ROLE = 'orchestrator' } else { $env:LOOM_TASK = $Task }
# Lets the context guard hook name this window when it rotates the session.
$env:LOOM_WINDOW_PID = $PID
Set-Location $WorkDir

$resume = @()
if ($SessionId) { $resume = @('--resume', $SessionId) }

if ($ClosePid) {
  # Once claude.cmd has started (cmd.exe or node.exe under this window; the job's own powershell.exe
  # and conhost.exe do not count), close the old window and everything under it. If claude never
  # starts, the old window is left alone.
  Start-Job -ScriptBlock {
    param($pidToClose, $me)
    $deadline = (Get-Date).AddSeconds(60)
    $started = $false
    while ((Get-Date) -lt $deadline -and -not $started) {
      $started = [bool](Get-CimInstance Win32_Process -Filter "ParentProcessId=$me" | Where-Object { $_.Name -in 'cmd.exe', 'node.exe' })
      if (-not $started) { Start-Sleep -Milliseconds 500 }
    }
    $old = Get-Process -Id $pidToClose -ErrorAction SilentlyContinue
    if ($started -and $old -and $old.ProcessName -eq 'powershell') {
      taskkill.exe /PID $pidToClose /T /F | Out-Null
    }
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
