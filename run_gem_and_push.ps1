# Fetch GeM Korba bids locally, then push to GitHub.
# GeM blocks GitHub Actions cloud servers — same as the CG portal.

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "Fetching GeM Korba bids locally..."
& $PythonExe run_gem.py --export-json --enrich-pdf
if ($LASTEXITCODE -ne 0) {
    Write-Host "GeM fetch failed."
    exit 1
}

$status = git status --porcelain docs/data/gem-tenders.json
if (-not $status) {
    Write-Host "No GeM data changes to push."
    exit 0
}

git add docs/data/gem-tenders.json
git commit -m "chore: update GeM tender data from local fetch"
git push

Write-Host "Done. Refresh the dashboard GeM view after GitHub Pages updates."
