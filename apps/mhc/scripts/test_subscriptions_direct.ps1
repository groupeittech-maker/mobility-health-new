# Script pour tester directement l'endpoint /api/v1/subscriptions
Write-Host "Test direct de l'endpoint /api/v1/subscriptions" -ForegroundColor Green
Write-Host "=" * 60

$baseUrl = "http://192.168.1.183:8000"

# Test 1: Vérifier que l'endpoint existe dans Swagger
Write-Host "`n1. Vérification dans Swagger..." -ForegroundColor Yellow
Write-Host "   Ouvrez: $baseUrl/docs" -ForegroundColor Cyan
Write-Host "   Cherchez: GET /api/v1/subscriptions" -ForegroundColor Cyan

# Test 2: Tester l'endpoint sans authentification (devrait retourner 401)
Write-Host "`n2. Test de l'endpoint sans authentification..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/subscriptions" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ⚠ Réponse inattendue: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "   Contenu: $($response.Content)" -ForegroundColor Cyan
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401) {
        Write-Host "   ✅ Endpoint accessible (401 attendu sans authentification)" -ForegroundColor Green
        Write-Host "   → L'endpoint fonctionne correctement!" -ForegroundColor Green
    } elseif ($statusCode -eq 404) {
        Write-Host "   ❌ Endpoint non trouvé (404)" -ForegroundColor Red
        Write-Host "   → Le router n'est pas enregistré" -ForegroundColor Yellow
        Write-Host "   → Redémarrez le serveur: .\scripts\restart_backend.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "   ⚠ Erreur: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "   Status: $statusCode" -ForegroundColor Yellow
    }
}

# Test 3: Vérifier avec un token (si disponible)
Write-Host "`n3. Test avec authentification..." -ForegroundColor Yellow
$token = Read-Host "   Entrez un token d'authentification (ou appuyez sur Entrée pour ignorer)"
if ($token) {
    try {
        $headers = @{
            "Authorization" = "Bearer $token"
        }
        $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/subscriptions" -Method GET -Headers $headers -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "   ✅ Endpoint accessible avec authentification" -ForegroundColor Green
        $json = $response.Content | ConvertFrom-Json
        Write-Host "   Nombre de souscriptions: $($json.Count)" -ForegroundColor Cyan
        if ($json.Count -gt 0) {
            Write-Host "   Première souscription:" -ForegroundColor Cyan
            $json[0] | ConvertTo-Json -Depth 2 | Write-Host -ForegroundColor Gray
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 401) {
            Write-Host "   ⚠ Token invalide ou expiré (401)" -ForegroundColor Yellow
        } elseif ($statusCode -eq 404) {
            Write-Host "   ❌ Endpoint non trouvé (404)" -ForegroundColor Red
        } else {
            Write-Host "   ⚠ Erreur: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   Test ignoré (pas de token fourni)" -ForegroundColor Gray
}

Write-Host "`n" + ("=" * 60)
Write-Host "Test terminé!" -ForegroundColor Green
