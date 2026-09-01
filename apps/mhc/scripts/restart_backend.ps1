# Script pour redémarrer le backend
Write-Host "Redémarrage du backend Mobility Health..." -ForegroundColor Green
Write-Host ""

# Arrêter tous les processus Python qui exécutent uvicorn
Write-Host "Arrêt des processus uvicorn existants..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*app.main*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Démarrage du backend..." -ForegroundColor Green
Write-Host ""

# Démarrer le backend
& ".\scripts\start_backend.ps1"

