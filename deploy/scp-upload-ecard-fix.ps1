# Deploiement correctif e-carte (URL proxy au lieu de minio:9000) via SCP
# Usage: .\deploy\scp-upload-ecard-fix.ps1
# Prerequis: acces SSH au serveur (mot de passe ou cle).

$ErrorActionPreference = "Stop"
# Racine du projet = dossier qui contient docker-compose.yml (parent du dossier deploy)
$ProjectRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    $ProjectRoot = "d:\logiciel et application\Mobility Health Nouveau"
}

# --- Config serveur (adapter si besoin) ---
$SSH_USER = "root"
$SSH_HOST = "srv1324425.hstgr.cloud"
$REMOTE_PATH = "/var/www/Mobility_Health/Mobility_Health"

$Remote = "${SSH_USER}@${SSH_HOST}"

Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploiement correctif e-carte (SCP)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1) docker-compose.yml (contient API_PUBLIC_BASE_URL)
Write-Host "Copie docker-compose.yml ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "docker-compose.yml" "${Remote}:${REMOTE_PATH}/"
if (-not $?) { Write-Host "Erreur copie docker-compose.yml" -ForegroundColor Red; exit 1 }

# 2) Fichiers backend du correctif e-carte
Write-Host "Copie app/core/config.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/core/config.py" "${Remote}:${REMOTE_PATH}/app/core/"
if (-not $?) { Write-Host "Erreur copie config.py" -ForegroundColor Red; exit 1 }

Write-Host "Copie app/core/security.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/core/security.py" "${Remote}:${REMOTE_PATH}/app/core/"
if (-not $?) { Write-Host "Erreur copie security.py" -ForegroundColor Red; exit 1 }

Write-Host "Copie app/api/v1/attestations.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/api/v1/attestations.py" "${Remote}:${REMOTE_PATH}/app/api/v1/"
if (-not $?) { Write-Host "Erreur copie attestations.py" -ForegroundColor Red; exit 1 }

Write-Host "Copie app/api/v1/auth.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/api/v1/auth.py" "${Remote}:${REMOTE_PATH}/app/api/v1/"
if (-not $?) { Write-Host "Erreur copie auth.py" -ForegroundColor Red; exit 1 }

Write-Host "Copie app/services/attestation_service.py ..." -ForegroundColor Cyan
& scp -o StrictHostKeyChecking=no "app/services/attestation_service.py" "${Remote}:${REMOTE_PATH}/app/services/"
if (-not $?) { Write-Host "Erreur copie attestation_service.py" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "OK. Tous les fichiers ont ete copies." -ForegroundColor Green
Write-Host ""
Write-Host "Sur le serveur :" -ForegroundColor Yellow
Write-Host "  1) Ajouter dans .env (si pas deja fait) :" -ForegroundColor White
Write-Host "     API_PUBLIC_BASE_URL=https://srv1324425.hstgr.cloud" -ForegroundColor Gray
Write-Host ""
Write-Host "  2) Redemarrer l'API :" -ForegroundColor White
Write-Host "     ssh $Remote" -ForegroundColor Gray
Write-Host "     cd $REMOTE_PATH" -ForegroundColor Gray
Write-Host "     docker compose restart api" -ForegroundColor Gray
Write-Host ""
