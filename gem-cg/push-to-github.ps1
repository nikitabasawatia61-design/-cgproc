# Push gem-cg to its own GitHub repo (gem-cg-korba)
# Run AFTER creating empty repo at https://github.com/new

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectDir

$RepoUrl = "https://github.com/nikitabasawatia61-design/gem-cg-korba.git"
$Branch = "gem-cg-standalone"

Write-Host "Working in: $ProjectDir"
Write-Host "Creating subtree branch from gem-cg/ ..."
git subtree split --prefix=gem-cg -b $Branch

Write-Host "Pushing to $RepoUrl ..."
git push -u $RepoUrl "${Branch}:main"

Write-Host ""
Write-Host "Done. Next:"
Write-Host "  1. Enable GitHub Pages (Actions) on gem-cg-korba"
Write-Host "  2. Create Vercel project linked to gem-cg-korba"
Write-Host "  3. Dashboard: https://nikitabasawatia61-design.github.io/gem-cg-korba/"
