# Script de diagnostic pour vérifier l'endpoint invoices
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Vérification de l'endpoint /invoices" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que le serveur backend est démarré
Write-Host "1. Vérification du serveur backend..." -ForegroundColor Yellow
$backendProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*app.main*"
}

if ($backendProcess) {
    Write-Host "   ✅ Serveur backend détecté (PID: $($backendProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "   ❌ Serveur backend non détecté" -ForegroundColor Red
    Write-Host "   → Démarrez-le avec: .\scripts\start_backend.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host ""
Write-Host "2. Vérification de l'import du module invoices..." -ForegroundColor Yellow

# Activer l'environnement virtuel si disponible
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
}

# Tester l'import
$importTest = python -c "
try:
    from app.api.v1 import invoices
    print('OK')
    print(f'Routes: {len(invoices.router.routes)}')
    for route in invoices.router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f'  - {list(route.methods)} {route.path}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

if ($importTest -match "OK") {
    Write-Host "   ✅ Module invoices importé avec succès" -ForegroundColor Green
    Write-Host "   $importTest" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Erreur lors de l'import du module invoices" -ForegroundColor Red
    Write-Host "   $importTest" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "3. Test de l'endpoint API..." -ForegroundColor Yellow

# Tester l'endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/invoices?limit=1" -Method GET -ErrorAction Stop
    Write-Host "   ✅ Endpoint accessible (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   ⚠️  Endpoint accessible mais nécessite une authentification (401)" -ForegroundColor Yellow
        Write-Host "   → C'est normal, l'endpoint fonctionne mais nécessite un token d'authentification" -ForegroundColor Cyan
    } elseif ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   ❌ Endpoint non trouvé (404)" -ForegroundColor Red
        Write-Host "   → Vérifiez que le serveur backend a été redémarré après les modifications" -ForegroundColor Cyan
        Write-Host "   → Redémarrez avec: .\scripts\restart_backend.ps1" -ForegroundColor Cyan
    } else {
        Write-Host "   ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Diagnostic terminé" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
