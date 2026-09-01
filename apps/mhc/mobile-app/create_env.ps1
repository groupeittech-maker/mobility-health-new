# Script pour créer le fichier .env
# Exécutez ce script avec: .\create_env.ps1

$envContent = @"
# Configuration API - Backend Hostinger (production)
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud
API_TIMEOUT=30000

# Environment (development ou production)
ENVIRONMENT=production

# App Configuration
APP_NAME=Mobility Health
APP_VERSION=1.0.0
"@

# Créer le fichier .env.example
$envContent | Out-File -FilePath ".env.example" -Encoding UTF8

# Créer le fichier .env
if (-not (Test-Path ".env")) {
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Fichier .env créé avec succès!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Le fichier .env existe déjà." -ForegroundColor Yellow
    Write-Host "Voulez-vous le remplacer? (O/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "O" -or $response -eq "o") {
        $envContent | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "✅ Fichier .env mis à jour!" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "📝 URL par défaut : backend Hostinger (srv1324425.hstgr.cloud)" -ForegroundColor Cyan
Write-Host "   Pour le développement local, modifiez .env :" -ForegroundColor Cyan
Write-Host "   - Android Emulator: http://10.0.2.2:8000/api/v1" -ForegroundColor Cyan
Write-Host "   - iOS Simulator: http://localhost:8000/api/v1" -ForegroundColor Cyan
Write-Host "   - Appareil physique: http://VOTRE_IP:8000/api/v1" -ForegroundColor Cyan


