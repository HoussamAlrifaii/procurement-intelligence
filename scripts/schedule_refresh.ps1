# Registers the monthly refresh in Windows Task Scheduler (run once, from the project folder):
#   powershell -ExecutionPolicy Bypass -File scripts\schedule_refresh.ps1
# Remove it again with:
#   schtasks /Delete /TN "TenderLens monthly refresh" /F
#
# The task runs on the 1st of each month at 07:00 with the project's .venv, and
# writes its output to logs\refresh_<date>.log. If the computer is off at that
# time, Windows runs it at the next start ("run as soon as possible").

$ErrorActionPreference = "Stop"
$TaskName = "TenderLens monthly refresh"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "No virtual environment found at $Python. Create it first (see README, Quick start)."
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m procurement.refresh" -WorkingDirectory $ProjectDir
# New-ScheduledTaskTrigger has no monthly option, so the task is created with schtasks
# and then given the action and settings above.
schtasks /Create /TN $TaskName /SC MONTHLY /D 1 /ST 07:00 /TR "cmd /c exit" /F | Out-Null
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Set-ScheduledTask -TaskName $TaskName -Action $Action -Settings $Settings | Out-Null

Write-Host "Scheduled '$TaskName': 1st of every month at 07:00."
Write-Host "Run it now to test:  schtasks /Run /TN `"$TaskName`""
