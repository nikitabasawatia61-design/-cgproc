# Windows Task Scheduler setup for daily tender fetch
# Run this once in PowerShell (as Administrator is not required):
#   .\schedule_daily.ps1

$ProjectDir = $PSScriptRoot
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Script = Join-Path $ProjectDir "run_daily.py"
$LogDir = Join-Path $ProjectDir "logs"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Virtual environment not found at $PythonExe"
    Write-Host "Using system python instead..."
    $PythonExe = "python"
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$TaskName = "CGProcDailyTenderFetch"
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$Script`" --headless" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "6:00AM"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Fetch new tenders from CG e-procurement portal daily" `
    -Force

Write-Host ""
Write-Host "Scheduled task '$TaskName' created."
Write-Host "  Runs daily at 6:00 AM"
Write-Host "  Command: $PythonExe `"$Script`" --headless"
Write-Host ""
Write-Host "To run manually now:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To remove:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
