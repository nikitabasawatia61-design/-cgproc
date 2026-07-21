# Run scraper locally, then push updated data to GitHub.
# Use this instead of GitHub Actions if the portal blocks cloud servers.

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "Running local scraper..."
& $PythonExe run_daily.py --headless --import-json --export-json
if ($LASTEXITCODE -ne 0) {
    Write-Host "Scraper finished with errors. Continuing to push if data changed."
}

$status = git status --porcelain docs/data/tenders.json
if (-not $status) {
    Write-Host "No tender data changes to push."
    exit 0
}

git add docs/data/tenders.json
git commit -m "chore: update tender data from local scraper"
Write-Host "Syncing with GitHub before push..."
git fetch origin main
$behind = git rev-list --count HEAD..origin/main
if ([int]$behind -gt 0) {
    Write-Host "Remote has $behind new commit(s). Pulling with rebase..."
    git pull --rebase origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PUSH BLOCKED: merge conflict. Resolve, then push again."
        exit 1
    }
}

git push origin main

Write-Host "Done. Dashboard will update after GitHub Pages refreshes."
