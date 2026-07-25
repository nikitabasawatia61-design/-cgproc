# Legacy wrapper: scrape first, then ask before pushing.
# Prefer the two-step flow: .\run_scrape.ps1  then  .\run_push.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

& "$ProjectDir\run_scrape.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Scrape failed or had errors. Not pushing."
    exit $LASTEXITCODE
}

Write-Host ""
$response = Read-Host "Push to GitHub now? (y/N)"
if ($response -match '^[yY]') {
    & "$ProjectDir\run_push.ps1"
} else {
    Write-Host "Skipped push. Run .\run_push.ps1 when ready."
}
