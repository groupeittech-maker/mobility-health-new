# Script pour tester l'endpoint /api/v1/subscriptions
Write-Host "Test de l'endpoint /api/v1/subscriptions" -ForegroundColor Green
Write-Host "=" * 60

$baseUrl = "http://192.168.1.183:8000"
if ($env:API_BASE_URL) {
    $baseUrl = $env:API_BASE_URL
}

# Test 1: Vérifier que le serveur backend est accessible
Write-Host "`n1. Vérification du serveur backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Backend accessible" -ForegroundColor Green
    Write-Host "   Réponse: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "   ✗ Backend non accessible: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Démarrez le backend avec: .\scripts\restart_backend.ps1" -ForegroundColor Yellow
    exit 1
}

# Test 2: Vérifier l'endpoint root pour voir l'état des routes
Write-Host "`n2. Vérification de l'état des routes..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $json = $response.Content | ConvertFrom-Json
    Write-Host "   ✓ Endpoint root accessible" -ForegroundColor Green
    
    if ($json.routes_status) {
        Write-Host "   État des routes:" -ForegroundColor Cyan
        $json.routes_status | ConvertTo-Json | Write-Host -ForegroundColor Gray
        
        if ($json.routes_status.subscriptions_router_loaded) {
            Write-Host "   ✓ Router subscriptions chargé" -ForegroundColor Green
            Write-Host "   Nombre de routes: $($json.routes_status.subscriptions_routes_count)" -ForegroundColor Cyan
        } elseif ($json.routes_status.subscriptions_router_error) {
            Write-Host "   ✗ Router subscriptions non chargé" -ForegroundColor Red
            Write-Host "   Erreur: $($json.routes_status.subscriptions_router_error)" -ForegroundColor Red
            Write-Host "   → Cette erreur doit être corrigée avant que l'endpoint fonctionne" -ForegroundColor Yellow
        } else {
            Write-Host "   ⚠ Informations de routes_status non disponibles" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠ routes_status non présent dans la réponse" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Erreur: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Tester l'endpoint /api/v1/subscriptions sans authentification (devrait retourner 401)
Write-Host "`n3. Test de l'endpoint /api/v1/subscriptions (sans token)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/subscriptions" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ⚠ Réponse inattendue: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "   Contenu: $($response.Content)" -ForegroundColor Cyan
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401) {
        Write-Host "   ✓ Endpoint accessible (401 attendu sans authentification)" -ForegroundColor Green
    } elseif ($statusCode -eq 404) {
        Write-Host "   ✗ Endpoint non trouvé (404)" -ForegroundColor Red
        Write-Host "   → L'endpoint n'est pas enregistré dans le serveur" -ForegroundColor Yellow
        Write-Host "   → Redémarrez le serveur backend: .\scripts\restart_backend.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "   ✗ Erreur: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "   Status: $statusCode" -ForegroundColor Red
    }
}

# Test 4: Vérifier les processus sur le port 8000
Write-Host "`n4. Vérification des processus sur le port 8000..." -ForegroundColor Yellow
$connections = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
if ($connections) {
    Write-Host "   ✓ Processus en écoute sur le port 8000:" -ForegroundColor Green
    $connections | ForEach-Object {
        $processId = ($_ -split '\s+')[-1]
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "      PID: $processId - $($process.ProcessName)" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "   ✗ Aucun processus en écoute sur le port 8000" -ForegroundColor Red
    Write-Host "   → Démarrez le backend: .\scripts\restart_backend.ps1" -ForegroundColor Yellow
}

# Test 5: Vérifier la documentation Swagger
Write-Host "`n5. Vérification de la documentation Swagger..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Documentation accessible" -ForegroundColor Green
    Write-Host "   → Ouvrez http://192.168.1.183:8000/docs pour voir tous les endpoints" -ForegroundColor Cyan
} catch {
    Write-Host "   ✗ Documentation non accessible: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n" + ("=" * 60)
Write-Host "Tests terminés!" -ForegroundColor Green
Write-Host ""
if ($json.routes_status.subscriptions_router_error) {
    Write-Host "❌ ERREUR DÉTECTÉE:" -ForegroundColor Red
    Write-Host "   Le router subscriptions ne peut pas être chargé." -ForegroundColor Red
    Write-Host "   Erreur: $($json.routes_status.subscriptions_router_error)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Solutions:" -ForegroundColor Yellow
    Write-Host "   1. Vérifiez les logs du serveur backend pour plus de détails" -ForegroundColor Cyan
    Write-Host "   2. Testez l'import: python -c 'from app.api.v1 import subscriptions'" -ForegroundColor Cyan
    Write-Host "   3. Vérifiez la syntaxe: python -m py_compile app\api\v1\subscriptions.py" -ForegroundColor Cyan
    Write-Host "   4. Réinstallez les dépendances: pip install -r requirements.txt" -ForegroundColor Cyan
} else {
    Write-Host "💡 Si l'endpoint retourne 404:" -ForegroundColor Yellow
    Write-Host "   1. Redémarrez le serveur backend: .\scripts\restart_backend.ps1" -ForegroundColor Cyan
    Write-Host "   2. Vérifiez les logs du serveur pour des erreurs d'import" -ForegroundColor Cyan
    Write-Host "   3. Vérifiez que app/api/v1/subscriptions.py existe et est valide" -ForegroundColor Cyan
    Write-Host "   4. Vérifiez que app/api/v1/__init__.py inclut le router subscriptions" -ForegroundColor Cyan
}
