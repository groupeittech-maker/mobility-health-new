# PowerShell script to start all Celery workers and beat
# Usage: .\scripts\start_all_workers.ps1

Write-Host "Démarrage de tous les workers Celery" -ForegroundColor Cyan

# Activer l'environnement virtuel si présent
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

Write-Host "`nDémarrage des workers en arrière-plan..." -ForegroundColor Green

# Démarrer le worker pour les notifications
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_celery_worker.ps1 -Queue notifications" -WindowStyle Minimized

# Démarrer le worker pour les rappels
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_celery_worker.ps1 -Queue reminders" -WindowStyle Minimized

# Démarrer le worker par défaut
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_celery_worker.ps1 -Queue default" -WindowStyle Minimized

# Attendre un peu avant de démarrer Beat
Start-Sleep -Seconds 2

# Démarrer Celery Beat
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_celery_beat.ps1" -WindowStyle Minimized

Write-Host "`n✅ Tous les workers ont été démarrés!" -ForegroundColor Green
Write-Host "`nWorkers démarrés:" -ForegroundColor Yellow
Write-Host "  - Worker notifications (queue: notifications)" -ForegroundColor White
Write-Host "  - Worker rappels (queue: reminders)" -ForegroundColor White
Write-Host "  - Worker par défaut (queue: default)" -ForegroundColor White
Write-Host "  - Celery Beat (scheduler)" -ForegroundColor White
Write-Host "`nPour arrêter les workers, fermez les fenêtres PowerShell correspondantes." -ForegroundColor Yellow

