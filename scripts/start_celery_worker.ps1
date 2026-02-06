# PowerShell script to start Celery worker
# Usage: .\scripts\start_celery_worker.ps1 [queue_name]

param(
    [string]$Queue = "default"
)

Write-Host "Démarrage du worker Celery pour la queue: $Queue" -ForegroundColor Cyan

# Activer l'environnement virtuel si présent
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Démarrer le worker Celery
Write-Host "`nDémarrage du worker Celery..." -ForegroundColor Green
Write-Host "Queue: $Queue" -ForegroundColor Green
Write-Host "Appuyez sur Ctrl+C pour arrêter`n" -ForegroundColor Yellow

# Sur Windows, utiliser le pool 'solo' au lieu de 'prefork'
celery -A app.core.celery_app:celery_app worker `
    --loglevel=info `
    --pool=solo `
    --queues=$Queue `
    --hostname=worker@%h
