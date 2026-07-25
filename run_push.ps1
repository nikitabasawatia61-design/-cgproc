# Step 2: Push tender data to GitHub after a successful scrape.
# Run only after .\run_scrape.ps1 shows a good FINAL SUMMARY.

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$JsonPath = Join-Path $ProjectDir "docs\data\tenders.json"

Write-Host ""
Write-Host "=== STEP 2: PUSH TO GITHUB ==="

if (Test-Path ".git/rebase-merge") {
    Write-Host "Stuck git rebase detected. Aborting..."
    git rebase --abort
    git checkout main 2>$null
}

Write-Host "Checking tenders.json..."
& python -c "import json; json.load(open(r'$JsonPath', encoding='utf-8')); print('JSON OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: tenders.json is invalid. Run .\run_scrape.ps1 first."
    exit 1
}

$status = git status --porcelain docs/data/tenders.json
if (-not $status) {
    Write-Host "No changes in docs/data/tenders.json to push."
    exit 0
}

git add docs/data/tenders.json
git commit -m "chore: update tender data from local scraper"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Nothing to commit."
    exit 0
}

Write-Host "Syncing with GitHub..."
git fetch origin main
$behind = git rev-list --count HEAD..origin/main
if ([int]$behind -gt 0) {
    Write-Host "Pulling $behind remote commit(s)..."
    git pull --rebase origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "PUSH BLOCKED: merge conflict in tenders.json."
        Write-Host "Fix: git checkout --ours docs/data/tenders.json"
        Write-Host "      git add docs/data/tenders.json"
        Write-Host "      git rebase --continue"
        Write-Host "      git push origin main"
        exit 1
    }
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "PUSH FAILED."
    exit 1
}

Write-Host ""
Write-Host "Done. Hard refresh the dashboard: Ctrl+F5"
