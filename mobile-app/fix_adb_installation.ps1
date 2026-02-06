# Script PowerShell pour résoudre les problèmes d'installation ADB

Write-Host "🔧 Résolution des problèmes d'installation ADB..." -ForegroundColor Cyan

# Étape 1: Vérifier la connexion ADB
Write-Host "`n📱 Vérification de la connexion ADB..." -ForegroundColor Yellow
$devices = adb devices
Write-Host $devices

# Étape 2: Redémarrer ADB
Write-Host "`n🔄 Redémarrage du serveur ADB..." -ForegroundColor Yellow
adb kill-server
Start-Sleep -Seconds 2
adb start-server
Start-Sleep -Seconds 2

# Étape 3: Vérifier à nouveau
Write-Host "`n📱 Vérification après redémarrage..." -ForegroundColor Yellow
$devices = adb devices
Write-Host $devices

# Étape 4: Désinstaller l'application existante si elle existe
Write-Host "`n🗑️  Tentative de désinstallation de l'application existante..." -ForegroundColor Yellow
$packageNames = @(
    "mobility.health.mobile",
    "com.example.mobility_health_mobile",
    "mobility_health_mobile"
)

foreach ($package in $packageNames) {
    Write-Host "   Tentative avec: $package" -ForegroundColor Gray
    $result = adb uninstall $package 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Application désinstallée: $package" -ForegroundColor Green
        break
    }
}

# Étape 5: Nettoyer Flutter
Write-Host "`n🧹 Nettoyage du build Flutter..." -ForegroundColor Yellow
flutter clean

# Étape 6: Reconstruire
Write-Host "`n🔨 Reconstruction de l'application..." -ForegroundColor Yellow
flutter pub get

# Étape 7: Instructions finales
Write-Host "`n✅ Étapes terminées!" -ForegroundColor Green
Write-Host "`n📋 Prochaines étapes:" -ForegroundColor Cyan
Write-Host "   1. Vérifiez que votre appareil est bien connecté et autorisé" -ForegroundColor White
Write-Host "   2. Sur l'appareil, autorisez l'ordinateur si une popup apparaît" -ForegroundColor White
Write-Host "   3. Vérifiez que le débogage USB est activé" -ForegroundColor White
Write-Host "   4. Exécutez: flutter run" -ForegroundColor White
Write-Host "`n💡 Si l'appareil est toujours 'offline':" -ForegroundColor Yellow
Write-Host "   - Débranchez et rebranchez le câble USB" -ForegroundColor White
Write-Host "   - Sur l'appareil: Paramètres → Options développeur → Révoquer les autorisations USB" -ForegroundColor White
Write-Host "   - Rebranchez et autorisez à nouveau" -ForegroundColor White

