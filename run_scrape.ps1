# Scrape tenders locally (visible browser). Does NOT push.
#
# Usage:
#   .\run_scrape.ps1           daily update
#   .\run_scrape.ps1 -FullScan first-time sync (every listing page)

param(
    [switch]$FullScan
)

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

if (Test-Path ".git/rebase-merge") { git rebase --abort 2>$null }
if (Test-Path ".git/rebase-apply") { git rebase --abort 2>$null }
if (Test-Path ".git/MERGE_HEAD") { git merge --abort 2>$null }

Write-Host ""
Write-Host "=== SCRAPE ==="
Write-Host "Phase 1: scan IDs until first tender already in database"
Write-Host "Phase 2: fetch details for new IDs only"
if ($FullScan) {
    Write-Host "Mode: FULL SCAN"
    $Args = @("run_daily.py", "--export-json", "--full-scan")
} else {
    Write-Host "Mode: DAILY"
    $Args = @("run_daily.py", "--export-json")
}
Write-Host ""

& $PythonExe @Args
exit $LASTEXITCODE
