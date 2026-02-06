# Script pour vérifier que l'endpoint /api/v1/subscriptions est accessible
Write-Host "🔍 Vérification de l'endpoint /api/v1/subscriptions..." -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://192.168.1.183:8000"
$endpoint = "$baseUrl/api/v1/subscriptions"

try {
    Write-Host "Test 1: Vérification de l'endpoint sans authentification..." -ForegroundColor Yellow
    $response = Invoke-WebRequest -Uri $endpoint -Method GET -TimeoutSec 5 -ErrorAction Stop
    
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor $(if ($response.StatusCode -eq 401) { "Green" } else { "Yellow" })
    
    if ($response.StatusCode -eq 401) {
        Write-Host "   ✅ Endpoint trouvé (401 attendu sans token)" -ForegroundColor Green
        Write-Host ""
        Write-Host "✅ L'endpoint est accessible mais nécessite une authentification" -ForegroundColor Green
    } elseif ($response.StatusCode -eq 404) {
        Write-Host "   ❌ Endpoint non trouvé (404)" -ForegroundColor Red
        Write-Host ""
        Write-Host "❌ PROBLÈME: L'endpoint n'est pas disponible" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Solutions:" -ForegroundColor Yellow
        Write-Host "   1. Redémarrer le serveur backend:" -ForegroundColor White
        Write-Host "      .\scripts\restart_backend.ps1" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   2. Vérifier que le serveur backend est démarré:" -ForegroundColor White
        Write-Host "      Get-Process python | Where-Object { `$_.CommandLine -like '*uvicorn*' }" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   3. Vérifier les logs du serveur pour des erreurs" -ForegroundColor White
    } else {
        Write-Host "   ⚠️  Status inattendu: $($response.StatusCode)" -ForegroundColor Yellow
        Write-Host "   Réponse: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))" -ForegroundColor Gray
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    
    if ($statusCode -eq 401) {
        Write-Host "   ✅ Endpoint trouvé (401 attendu sans token)" -ForegroundColor Green
        Write-Host ""
        Write-Host "✅ L'endpoint est accessible mais nécessite une authentification" -ForegroundColor Green
    } elseif ($statusCode -eq 404) {
        Write-Host "   ❌ Endpoint non trouvé (404)" -ForegroundColor Red
        Write-Host ""
        Write-Host "❌ PROBLÈME: L'endpoint n'est pas disponible" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Solutions:" -ForegroundColor Yellow
        Write-Host "   1. Redémarrer le serveur backend:" -ForegroundColor White
        Write-Host "      .\scripts\restart_backend.ps1" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   2. Vérifier que le serveur backend est démarré" -ForegroundColor White
    } else {
        Write-Host "   ❌ Erreur de connexion: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Vérifiez que le serveur backend est démarré sur $baseUrl" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Test 2: Vérification des routes disponibles..." -ForegroundColor Yellow
try {
    $rootUrl = "$baseUrl/api/v1/"
    $rootResponse = Invoke-WebRequest -Uri $rootUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
    $rootData = $rootResponse.Content | ConvertFrom-Json
    
    if ($rootData.endpoints) {
        Write-Host "   Endpoints disponibles:" -ForegroundColor Cyan
        foreach ($endpointName in $rootData.endpoints.PSObject.Properties.Name) {
            $endpointPath = $rootData.endpoints.$endpointName
            $marker = if ($endpointName -like "*subscription*") { "✅" } else { "  " }
            Write-Host "   $marker $endpointName : $endpointPath" -ForegroundColor $(if ($endpointName -like "*subscription*") { "Green" } else { "White" })
        }
    }
} catch {
    Write-Host "   ⚠️  Impossible de récupérer la liste des endpoints: $_" -ForegroundColor Yellow
}

Write-Host ""
