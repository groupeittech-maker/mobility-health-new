# Deploiement Mobility Health - UNIQUEMENT avec commandes SCP
# Usage: .\deploy\deploy-scp.ps1
# Depuis la racine du projet ou depuis deploy/
#
# --- Ce qui est mis a jour sur le serveur ---
# [1] Frontend : tout le dossier local "frontend-simple" -> /var/www/mobility-health/frontend-simple/
#     (pages HTML, CSS, JS du site statique / Nginx).
# [2] Backend  : "app" + "alembic" + fichiers Docker/requirements -> /var/www/Mobility_Health/Mobility_Health/
#     (code FastAPI, migrations Alembic, definition des images Docker). Sans rebuild Docker, l'API en
#     conteneur continue d'executer l'ancienne image : voir les commandes SSH affichees a la fin.

$ErrorActionPreference = "Stop"

# --- Configuration (Hostinger VPS actuel ; alternative : deployer@IP en commentaire) ---
$SSH_USER = "root"
$SSH_HOST = "srv1324425.hstgr.cloud"
# $SSH_USER = "deployer"
# $SSH_HOST = "82.112.242.86"
# Chemins : deploy/SCP-DEPLOY-CHEMINS.md
$REMOTE_BASE = "/var/www/mobility-health"
$SERVER_FRONTEND = "$REMOTE_BASE/frontend-simple"
$SERVER_BACKEND = "/var/www/Mobility_Health/Mobility_Health"

$Remote = "${SSH_USER}@${SSH_HOST}"

# Racine du projet (dossier parent de deploy)
$ProjectRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $ProjectRoot "app"))) {
    $ProjectRoot = "d:\logiciel et application\Mobility Health Nouveau"
}
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploiement SCP - Mobility Health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Serveur: $Remote" -ForegroundColor Gray
Write-Host ""

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: SCP non disponible. Installez OpenSSH Client." -ForegroundColor Red
    exit 1
}

# --- FRONTEND (dossier complet en SCP recursif) ---
Write-Host "[1] Frontend -> ${Remote}:${SERVER_FRONTEND}" -ForegroundColor Yellow
$frontendDir = "frontend-simple"
if (-not (Test-Path $frontendDir)) {
    Write-Host "    Ignore: $frontendDir absent" -ForegroundColor DarkGray
} else {
    # SCP en recursif : on copie le contenu vers le parent pour obtenir .../frontend-simple/
    # scp -r frontend-simple user@host:/var/www/mobility-health/ => .../frontend-simple/
    & scp -r -o StrictHostKeyChecking=no "$frontendDir" "${Remote}:${REMOTE_BASE}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    Echec SCP frontend" -ForegroundColor Red; exit 1 }
    Write-Host "    OK" -ForegroundColor Green
}

# --- BACKEND : dossiers (SCP recursif) ---
Write-Host "[2] Backend (dossiers) -> ${Remote}:${SERVER_BACKEND}" -ForegroundColor Yellow
foreach ($dir in @("app", "alembic")) {
    if (-not (Test-Path $dir)) { Write-Host "    Ignore: $dir absent" -ForegroundColor DarkGray; continue }
    Write-Host "    scp -r $dir ..." -ForegroundColor Gray
    & scp -r -o StrictHostKeyChecking=no "$dir" "${Remote}:${SERVER_BACKEND}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    Echec: $dir" -ForegroundColor Red; exit 1 }
}
Write-Host "    OK" -ForegroundColor Green

# --- BACKEND : fichiers a la racine ---
Write-Host "[3] Backend (fichiers) -> ${Remote}:${SERVER_BACKEND}" -ForegroundColor Yellow
$backendFiles = @(
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "Dockerfile",
    "Dockerfile.prod",
    "requirements.txt",
    "alembic.ini"
)
foreach ($f in $backendFiles) {
    if (-not (Test-Path $f)) { Write-Host "    Ignore: $f absent" -ForegroundColor DarkGray; continue }
    & scp -o StrictHostKeyChecking=no $f "${Remote}:${SERVER_BACKEND}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    Echec: $f" -ForegroundColor Red; exit 1 }
}
Write-Host "    OK" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Copie SCP terminee." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Sur le serveur, executer (SSH) :" -ForegroundColor Yellow
Write-Host "  ssh $Remote" -ForegroundColor White
Write-Host "  cd $SERVER_BACKEND" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml build api celery_worker celery_beat" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head" -ForegroundColor White
Write-Host "  systemctl reload nginx" -ForegroundColor White
Write-Host ""
Write-Host "Commandes SCP manuelles equivalentes (depuis la racine du projet) :" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no frontend-simple ${Remote}:${REMOTE_BASE}/" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no app alembic ${Remote}:${SERVER_BACKEND}/   # deux commandes separees recommandees :" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no app ${Remote}:${SERVER_BACKEND}/" -ForegroundColor DarkGray
Write-Host "  scp -r -o StrictHostKeyChecking=no alembic ${Remote}:${SERVER_BACKEND}/" -ForegroundColor DarkGray
Write-Host ""
