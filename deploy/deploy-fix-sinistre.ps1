# Déploie uniquement le correctif "sinistre à valider" (hospital_sinistres.py)
# Usage: .\deploy\deploy-fix-sinistre.ps1
# Prérequis: accès SSH au serveur (mot de passe ou clé).

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $ProjectRoot) { $ProjectRoot = "d:\logiciel et application\Mobility Health Nouveau" }

# --- À MODIFIER selon ton serveur (même config que deploy.ps1 ou scp-upload-changes.ps1) ---
$SSH_USER = "deployer"
$SSH_HOST = "82.112.242.86"
$SERVER_BACKEND = "/var/www/mobility-health/backend"

# Alternative si tu utilises l'hôte Hostinger :
# $SSH_USER = "root"
# $SSH_HOST = "srv1324425.hstgr.cloud"
# $SERVER_BACKEND = "/var/www/mobility-health/backend"

$Remote = "${SSH_USER}@${SSH_HOST}"
$RemoteApiPath = "${SERVER_BACKEND}/app/api/v1"

Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploiement correctif sinistre (medecin referent)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Copie de app/api/v1/hospital_sinistres.py vers ${Remote}:${RemoteApiPath}/ ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no -o ConnectTimeout=15 "app/api/v1/hospital_sinistres.py" "${Remote}:${RemoteApiPath}/"
if (-not $?) {
    Write-Host "Erreur: echec de la copie (SSH inaccessible? Verifiez SSH_HOST et acces reseau)." -ForegroundColor Red
    exit 1
}

Write-Host "OK. Fichier copie." -ForegroundColor Green
Write-Host ""
Write-Host "Sur le serveur, execute pour recharger l'API :" -ForegroundColor Yellow
Write-Host "  ssh $Remote" -ForegroundColor White
Write-Host "  cd $SERVER_BACKEND" -ForegroundColor White
Write-Host "  sudo docker compose build api" -ForegroundColor White
Write-Host "  sudo docker compose up -d api" -ForegroundColor White
Write-Host ""
Write-Host "Ou en prod avec docker-compose.prod.yml :" -ForegroundColor DarkGray
Write-Host "  sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build api" -ForegroundColor White
Write-Host "  sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api" -ForegroundColor White
Write-Host ""
