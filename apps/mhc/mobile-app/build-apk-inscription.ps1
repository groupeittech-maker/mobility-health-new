# Recompile l'APK avec le formulaire d'inscription simplifié (v1.0.0+3)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Fichier .env créé depuis .env.example — vérifiez l'URL API si besoin."
}

Write-Host "=== Nettoyage et dépendances ==="
flutter clean
flutter pub get

Write-Host "=== Test formulaire inscription ==="
flutter test test/register_screen_test.dart

Write-Host "=== Build APK release (peut prendre 5-15 min la 1ère fois) ==="
flutter build apk --release

$apk = Join-Path $PSScriptRoot "build\app\outputs\flutter-apk\app-release.apk"
if (Test-Path $apk) {
    Write-Host ""
    Write-Host "APK prêt :" -ForegroundColor Green
    Write-Host $apk
    Write-Host ""
    Write-Host "Installez sur le téléphone (USB + débogage USB) :"
    Write-Host "  adb install -r `"$apk`""
    Write-Host ""
    Write-Host "Vérification : écran S'inscrire doit afficher v1.0.0+3 en haut à droite."
} else {
    Write-Host "ERREUR : APK non trouvé." -ForegroundColor Red
    exit 1
}
