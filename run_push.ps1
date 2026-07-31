# Push tender data to GitHub Pages after a successful scrape.

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$JsonPath = Join-Path $ProjectDir "docs\data\tenders.json"
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

function Clear-StuckGit {
    if (Test-Path ".git/rebase-merge") {
        Write-Host "Aborting stuck rebase..."
        git rebase --abort
    }
    if (Test-Path ".git/rebase-apply") {
        Write-Host "Aborting stuck rebase..."
        git rebase --abort
    }
    if (Test-Path ".git/MERGE_HEAD") {
        Write-Host "Aborting stuck merge..."
        git merge --abort
    }
}

function Export-FromDb {
    & $PythonExe -c "import database as db; db.init_db(); db.repair_tenders_json(); db.export_to_json(); print('Exported', db.tender_count(), 'tenders from local DB')"
    return $LASTEXITCODE -eq 0
}

Write-Host ""
Write-Host "=== PUSH TO WEB ==="

Clear-StuckGit

if (-not (Export-FromDb)) {
    Write-Host "ERROR: could not export tenders.json. Run scrape first."
    exit 1
}

& $PythonExe -c "import json; json.load(open(r'$JsonPath', encoding='utf-8')); print('JSON OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: tenders.json is invalid."
    exit 1
}

Write-Host "Syncing with GitHub..."
git fetch origin main 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: could not fetch from GitHub. Pushing local commit only..."
}

$behind = 0
try { $behind = [int](git rev-list --count HEAD..origin/main 2>$null) } catch { $behind = 0 }

if ($behind -gt 0) {
    Write-Host "Merging $behind remote commit(s) (keeping local tender data)..."
    git merge origin/main -X ours --no-edit
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Merge failed. Aborting..."
        git merge --abort 2>$null
        exit 1
    }
    Export-FromDb | Out-Null
}

$status = git status --porcelain docs/data/tenders.json
if ($status) {
    git add docs/data/tenders.json
    git commit -m "chore: update tender data from local scraper"
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "PUSH FAILED. Check internet / GitHub login."
    exit 1
}

Write-Host ""
Write-Host "Done. Dashboard: https://nikitabasawatia61-design.github.io/-cgproc/"
Write-Host "Hard refresh: Ctrl+F5"
