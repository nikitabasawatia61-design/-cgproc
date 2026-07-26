# Step 1: Scrape tenders locally (visible browser).
# Does NOT push to GitHub. When FINAL SUMMARY looks good, run .\run_push.ps1
#
# Usage:
#   .\run_scrape.ps1           daily update (pages 1, 2, 3... until no new tenders)
#   .\run_scrape.ps1 -FullScan every portal page (slow, first-time sync)

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
Write-Host "New tenders appear on page 1, 2, 3... (forward only, no jumping back)."
if ($FullScan) {
    Write-Host "Mode: FULL SCAN (all listing pages)"
    $Args = @("run_daily.py", "--import-json", "--export-json", "--full-scan")
} else {
    Write-Host "Mode: DAILY (stop when a page has no new tenders)"
    $Args = @("run_daily.py", "--import-json", "--export-json")
}
Write-Host ""

& $PythonExe @Args
exit $LASTEXITCODE
