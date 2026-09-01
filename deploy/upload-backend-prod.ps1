# Backend uniquement : copie SCP vers le VPS puis instructions Docker.
# Usage (PowerShell, racine du repo) : .\deploy\upload-backend-prod.ps1
#
# --- Ce qui est mis a jour (PAS le frontend) ---
# - app/          : code Python FastAPI (routes, services, modeles, workers references par Celery).
# - alembic/      : migrations base de donnees (a appliquer avec alembic upgrade head dans le conteneur api).
# - docker-compose*.yml, Dockerfile* : definition des images / services (api, celery_worker, celery_beat).
# - requirements.txt, alembic.ini : dependances Python et config Alembic.
#
# Chemin distant : dossier ou vous lancez "docker compose" en production (sans espace dans le nom).
# Voir deploy/SCP-DEPLOY-CHEMINS.md — ne pas confondre avec .../Mobility Health/ (site statique).

$ErrorActionPreference = "Stop"
$SSH_USER = "root"
$SSH_HOST = "srv1324425.hstgr.cloud"
$SERVER_BACKEND = "/var/www/Mobility_Health/Mobility_Health"
$Remote = "${SSH_USER}@${SSH_HOST}"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "Installez OpenSSH Client (scp)." -ForegroundColor Red
    exit 1
}

Write-Host "Copie backend -> ${Remote}:${SERVER_BACKEND}/" -ForegroundColor Cyan
foreach ($dir in @("app", "alembic")) {
    if (-not (Test-Path $dir)) { continue }
    scp -r -o StrictHostKeyChecking=no "$dir" "${Remote}:${SERVER_BACKEND}/"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$backendFiles = @(
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "Dockerfile",
    "Dockerfile.prod",
    "requirements.txt",
    "alembic.ini"
)
foreach ($f in $backendFiles) {
    if (-not (Test-Path $f)) { continue }
    scp -o StrictHostKeyChecking=no $f "${Remote}:${SERVER_BACKEND}/"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Copie terminee." -ForegroundColor Green
Write-Host ""
Write-Host "Commandes SCP manuelles equivalentes :" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no app ${Remote}:${SERVER_BACKEND}/" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no alembic ${Remote}:${SERVER_BACKEND}/" -ForegroundColor DarkGray
Write-Host "  scp -o StrictHostKeyChecking=no docker-compose.yml docker-compose.prod.yml Dockerfile Dockerfile.prod requirements.txt alembic.ini ${Remote}:${SERVER_BACKEND}/" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Sur le serveur (obligatoire pour prendre en compte le nouveau code) :" -ForegroundColor Yellow
Write-Host "  cd $SERVER_BACKEND" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml build api celery_worker celery_beat" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head" -ForegroundColor White
Write-Host "  systemctl reload nginx" -ForegroundColor White
