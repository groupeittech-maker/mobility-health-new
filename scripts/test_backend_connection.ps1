# Script pour tester la connexion au backend
Write-Host "Test de connexion au backend Mobility Health" -ForegroundColor Green
Write-Host "=" * 60

# Test 1: Health check
Write-Host "`n1. Test du endpoint /health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "   ✓ Backend accessible" -ForegroundColor Green
    Write-Host "   Réponse: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "   ✗ Backend non accessible: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Test de l'endpoint de login
Write-Host "`n2. Test de l'endpoint /api/v1/auth/login..." -ForegroundColor Yellow
try {
    $body = @{
        username = "test"
        password = "test"
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Endpoint accessible" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Cyan
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   ✓ Endpoint accessible (401 attendu pour identifiants incorrects)" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Erreur: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "   Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}

# Test 3: Test avec FormData (comme le frontend)
Write-Host "`n3. Test avec FormData (comme le frontend)..." -ForegroundColor Yellow
try {
    $formData = @{
        username = "test"
        password = "test"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $formData -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Endpoint accessible avec FormData" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   ✓ Endpoint accessible avec FormData (401 attendu)" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 4: Vérifier les processus
Write-Host "`n4. Vérification des processus sur le port 8000..." -ForegroundColor Yellow
$connections = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
if ($connections) {
    Write-Host "   ✓ Processus en écoute sur le port 8000:" -ForegroundColor Green
    $connections | ForEach-Object {
        $pid = ($_ -split '\s+')[-1]
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "      PID: $pid - $($process.ProcessName)" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "   ✗ Aucun processus en écoute sur le port 8000" -ForegroundColor Red
}

Write-Host "`n" + ("=" * 60)
Write-Host "Tests terminés!" -ForegroundColor Green
Write-Host "`nSi tous les tests passent mais que le frontend ne peut toujours pas se connecter:" -ForegroundColor Yellow
Write-Host "  1. Vérifiez que le frontend est servi via HTTP (pas file://)" -ForegroundColor Cyan
Write-Host "  2. Vérifiez l'URL dans frontend-simple/js/api.js" -ForegroundColor Cyan
Write-Host "  3. Ouvrez la console du navigateur (F12) pour voir les erreurs CORS" -ForegroundColor Cyan
