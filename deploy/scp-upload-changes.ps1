# Copie des fichiers modifiés (fix enum statutprojetvoyage) vers le serveur
# Usage: .\deploy\scp-upload-changes.ps1
# Tu seras invité à saisir le mot de passe SSH si besoin.

$ErrorActionPreference = "Stop"
$ProjectRoot = "d:\logiciel et application\Mobility Health Nouveau"

# --- À MODIFIER selon ton serveur ---
$SSH_USER = "root"
$SSH_HOST = "srv1324425.hstgr.cloud"
$REMOTE_PATH = "/var/www/mobility-health"   # ou /root/mobility-health selon où est le projet

$Remote = "${SSH_USER}@${SSH_HOST}"

Set-Location $ProjectRoot

Write-Host "Copie de app/api/v1/voyages.py vers ${Remote}:${REMOTE_PATH}/app/api/v1/ ..." -ForegroundColor Cyan
scp app/api/v1/voyages.py "${Remote}:${REMOTE_PATH}/app/api/v1/"

Write-Host "Copie de app/models/projet_voyage.py vers ${Remote}:${REMOTE_PATH}/app/models/ ..." -ForegroundColor Cyan
scp app/models/projet_voyage.py "${Remote}:${REMOTE_PATH}/app/models/"

Write-Host "OK. Fichiers copiés." -ForegroundColor Green
Write-Host ""
Write-Host "Sur le serveur, exécute pour redémarrer l'API :" -ForegroundColor Yellow
Write-Host "  ssh $Remote" -ForegroundColor White
Write-Host "  cd $REMOTE_PATH" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml build api" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api" -ForegroundColor White
