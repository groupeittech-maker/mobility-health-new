# PowerShell script to start Celery Beat (scheduler)
# Usage: .\scripts\start_celery_beat.ps1

Write-Host "Démarrage de Celery Beat (scheduler)" -ForegroundColor Cyan

# Activer l'environnement virtuel si présent
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Démarrer Celery Beat
Write-Host "`nDémarrage de Celery Beat..." -ForegroundColor Green
Write-Host "Appuyez sur Ctrl+C pour arrêter`n" -ForegroundColor Yellow

celery -A app.core.celery_app:celery_app beat `
    --loglevel=info
