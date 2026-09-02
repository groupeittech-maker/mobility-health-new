# Synchronise le dépôt local avec main après un déploiement CI/CD.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Sync local <- origin/main ==" -ForegroundColor Cyan
git fetch origin main

$current = git branch --show-current
if ($current -ne "main") {
    Write-Host "Branche actuelle : $current -> bascule sur main"
    git checkout main
}

git pull --ff-only origin main
$sha = git rev-parse --short HEAD
Write-Host "OK Local a jour avec main ($sha)" -ForegroundColor Green
