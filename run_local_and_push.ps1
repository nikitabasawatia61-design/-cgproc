# Daily one-command flow: scrape -> push to web. No prompts.

param(
    [switch]$FullScan
)

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host ""
Write-Host "=== CG TENDER TRACKER — SCRAPE + PUSH ==="

if ($FullScan) {
    & "$ProjectDir\run_scrape.ps1" -FullScan
} else {
    & "$ProjectDir\run_scrape.ps1"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Scrape failed. Not pushing."
    exit $LASTEXITCODE
}

& "$ProjectDir\run_push.ps1"
exit $LASTEXITCODE
