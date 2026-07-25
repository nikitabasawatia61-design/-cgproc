# Step 1: Scrape tenders locally (visible browser — watch captcha/pagination).
# Does NOT push to GitHub. When FINAL SUMMARY looks good, run .\run_push.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host ""
Write-Host "=== STEP 1: SCRAPE (no git push) ==="
Write-Host "Chrome will open so you can see captcha and page navigation."
Write-Host ""

& $PythonExe run_daily.py --import-json --export-json
exit $LASTEXITCODE
