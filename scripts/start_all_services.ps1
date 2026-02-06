# PowerShell script to start all Mobility Health services
# This script starts: Backend, Frontend, Dependencies (PostgreSQL, Redis, Minio), and Celery Workers

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mobility Health - Démarrage complet" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "Répertoire du projet: $projectRoot" -ForegroundColor Yellow
Write-Host ""

# Step 1: Start Dependencies (PostgreSQL, Redis, Minio)
Write-Host "📦 Étape 1/4: Démarrage des dépendances (PostgreSQL, Redis, Minio)..." -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 1

if (Test-Path "scripts\start_dependencies.ps1") {
    & "scripts\start_dependencies.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Attention: Les dépendances n'ont pas pu démarrer. Vérifiez Docker." -ForegroundColor Yellow
        Write-Host "   Vous pouvez continuer si les services sont déjà en cours d'exécution." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Script start_dependencies.ps1 non trouvé. Ignoré." -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 2

# Step 2: Start Backend
Write-Host "🔧 Étape 2/4: Démarrage du Backend (FastAPI)..." -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\scripts\start_backend.ps1" -WindowStyle Normal

Write-Host "✅ Backend en cours de démarrage dans une nouvelle fenêtre..." -ForegroundColor Green
Write-Host "   URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 3

# Step 3: Start Frontend
Write-Host "🎨 Étape 3/4: Démarrage du Frontend..." -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\scripts\start_frontend.ps1" -WindowStyle Normal

Write-Host "✅ Frontend en cours de démarrage dans une nouvelle fenêtre..." -ForegroundColor Green
Write-Host "   URL: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Login: http://localhost:3000/login.html" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 2

# Step 4: Start Celery Workers (optional)
Write-Host "⚙️  Étape 4/4: Démarrage des Workers Celery (optionnel)..." -ForegroundColor Green
Write-Host ""
$response = Read-Host "Voulez-vous démarrer les workers Celery? (O/N)"
if ($response -eq "O" -or $response -eq "o" -or $response -eq "Y" -or $response -eq "y") {
    if (Test-Path "scripts\start_all_workers.ps1") {
        & "scripts\start_all_workers.ps1"
        Write-Host "✅ Workers Celery démarrés!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Script start_all_workers.ps1 non trouvé. Ignoré." -ForegroundColor Yellow
    }
} else {
    Write-Host "⏭️  Workers Celery ignorés." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ Tous les services sont lancés!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Résumé des services:" -ForegroundColor Yellow
Write-Host "   • Backend API:     http://localhost:8000" -ForegroundColor White
Write-Host "   • Frontend:        http://localhost:3000" -ForegroundColor White
Write-Host "   • PostgreSQL:      localhost:5432" -ForegroundColor White
Write-Host "   • Redis:           localhost:6379" -ForegroundColor White
Write-Host "   • Minio Console:   http://localhost:9001" -ForegroundColor White
Write-Host ""
Write-Host "🔗 Liens utiles:" -ForegroundColor Yellow
Write-Host "   • Page de connexion:  http://localhost:3000/login.html" -ForegroundColor Cyan
Write-Host "   • Documentation API:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  Note: Gardez toutes les fenêtres PowerShell ouvertes pour que les services continuent de fonctionner." -ForegroundColor Yellow
Write-Host "   Pour arrêter les services, fermez les fenêtres correspondantes." -ForegroundColor Yellow
Write-Host ""
