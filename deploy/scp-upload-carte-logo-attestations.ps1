# SCP : e-carte (silhouette, logo officiel) + attestations PDF + message admin regenerate-ecard
# Usage : .\deploy\scp-upload-carte-logo-attestations.ps1
# Serveur : deploy/SCP-DEPLOY-CHEMINS.md

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

$files = @(
    @{ Local = "app/services/card_service.py"; RemoteDir = "${REMOTE_PATH}/app/services/" }
    @{ Local = "app/services/pdf_service.py"; RemoteDir = "${REMOTE_PATH}/app/services/" }
    @{ Local = "app/api/v1/admin_subscriptions.py"; RemoteDir = "${REMOTE_PATH}/app/api/v1/" }
    @{ Local = "frontend-simple/assets/logo_officiel_mh.png"; RemoteDir = "${REMOTE_PATH}/frontend-simple/assets/" }
)

foreach ($item in $files) {
    if (-not (Test-Path $item.Local)) {
        Write-Host "Manquant (ignore ou erreur) : $($item.Local)" -ForegroundColor Red
        exit 1
    }
    Write-Host "Copie $($item.Local) ..." -ForegroundColor Cyan
    & scp -o StrictHostKeyChecking=no $item.Local "${Remote}:$($item.RemoteDir)"
    if (-not $?) { exit 1 }
}

Write-Host "OK. Fichiers copies." -ForegroundColor Green
Write-Host ""
Write-Host "Sur le VPS :" -ForegroundColor Yellow
Write-Host "  cd $REMOTE_PATH" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml build api celery_worker celery_beat" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "PNG e-cartes et PDF deja emis : regenerez si besoin (admin)." -ForegroundColor DarkGray
