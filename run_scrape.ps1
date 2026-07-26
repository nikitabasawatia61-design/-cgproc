# Step 1: Scrape tenders locally (visible browser).
# Does NOT push to GitHub. When FINAL SUMMARY looks good, run .\run_push.ps1
#
# Daily flow:
#   Page 1 IDs → if none in DB, page 2 → ... → stop at first ID already saved
#   Then fetch details for new IDs only
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

Write-Host ""
Write-Host "=== STEP 1: SCRAPE (no git push) ==="
Write-Host "Phase 1: scan IDs page 1, 2, 3... until first tender already in database"
Write-Host "Phase 2: fetch details for new IDs only"
if ($FullScan) {
    Write-Host "Mode: FULL SCAN"
    $Args = @("run_daily.py", "--import-json", "--export-json", "--full-scan")
} else {
    Write-Host "Mode: DAILY"
    $Args = @("run_daily.py", "--import-json", "--export-json")
}
Write-Host ""

& $PythonExe @Args
exit $LASTEXITCODE
