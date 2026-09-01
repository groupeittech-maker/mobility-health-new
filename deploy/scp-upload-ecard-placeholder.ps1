# Mise a jour SCP : e-carte sans silhouette (card_service + message admin)
# Usage (PowerShell, depuis n'importe quel dossier) : .\deploy\scp-upload-ecard-placeholder.ps1
# Prerequis : acces SSH (cle ou mot de passe).

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    $ProjectRoot = "d:\logiciel et application\Mobility Health Nouveau"
}

$SSH_USER = "root"
$SSH_HOST = "srv1324425.hstgr.cloud"
$REMOTE_PATH = "/var/www/Mobility_Health/Mobility_Health"
$Remote = "${SSH_USER}@${SSH_HOST}"

Set-Location $ProjectRoot

Write-Host "Copie app/services/card_service.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/services/card_service.py" "${Remote}:${REMOTE_PATH}/app/services/"
if (-not $?) { exit 1 }

Write-Host "Copie app/api/v1/admin_subscriptions.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/api/v1/admin_subscriptions.py" "${Remote}:${REMOTE_PATH}/app/api/v1/"
if (-not $?) { exit 1 }

Write-Host "OK. Fichiers copies." -ForegroundColor Green
Write-Host ""
Write-Host "Sur le serveur, pour prendre en compte le code Python :" -ForegroundColor Yellow
Write-Host "  cd $REMOTE_PATH" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml build api celery_worker celery_beat" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "Les cartes PNG deja generees ne changent pas ; regenerez via admin si besoin." -ForegroundColor DarkGray
