# PowerShell script to create test users
# Usage: .\scripts\create_test_users.ps1

Write-Host "Création des utilisateurs de test..." -ForegroundColor Cyan

python scripts/create_test_users.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Script exécuté avec succès!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Erreur lors de l'exécution du script" -ForegroundColor Red
    exit 1
}

