# Génère une clé SSH dédiée au déploiement GitHub Actions (dossier apps/mhc/deploy-keys/)
$ErrorActionPreference = "Stop"

$MhcRoot = Split-Path $PSScriptRoot -Parent
$KeysDir = Join-Path $MhcRoot "deploy-keys"
$KeyPath = Join-Path $KeysDir "github_actions_mhc"

New-Item -ItemType Directory -Force -Path $KeysDir | Out-Null

if (Test-Path $KeyPath) {
    Write-Host "Une clé existe déjà : $KeyPath" -ForegroundColor Yellow
    Write-Host "Supprimez-la manuellement si vous voulez en regénérer une." -ForegroundColor Yellow
    exit 1
}

if (-not (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: ssh-keygen introuvable. Installez OpenSSH Client." -ForegroundColor Red
    exit 1
}

ssh-keygen -t ed25519 -C "github-actions-mhc" -f $KeyPath -N '""'

Write-Host ""
Write-Host "Clés créées dans apps/mhc/deploy-keys/" -ForegroundColor Green
Write-Host "  Privée (secret GitHub SSH_PRIVATE_KEY) : github_actions_mhc" -ForegroundColor Cyan
Write-Host "  Publique (VPS authorized_keys)         : github_actions_mhc.pub" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prochaines étapes : voir deploy-keys/README.md" -ForegroundColor Gray
