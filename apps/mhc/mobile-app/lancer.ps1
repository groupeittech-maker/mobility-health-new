# Script PowerShell pour lancer l'application mobile Flutter
# Usage: .\lancer.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Lancement de l'application mobile" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que nous sommes dans le bon répertoire
if (-not (Test-Path "pubspec.yaml")) {
    Write-Host "ERREUR: Vous devez être dans le dossier mobile-app" -ForegroundColor Red
    Write-Host "Changez de répertoire avec: cd mobile-app" -ForegroundColor Yellow
    exit 1
}

Write-Host "Vérification des appareils disponibles..." -ForegroundColor Green
flutter devices
Write-Host ""

Write-Host "Lancement de l'application..." -ForegroundColor Green
flutter run

