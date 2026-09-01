# Script d'installation de Flutter pour Windows
# Exécutez avec: .\install_flutter.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation de Flutter SDK" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Flutter est déjà installé
$flutterPath = Get-Command flutter -ErrorAction SilentlyContinue
if ($flutterPath) {
    Write-Host "✅ Flutter est déjà installé !" -ForegroundColor Green
    Write-Host "Chemin: $($flutterPath.Source)" -ForegroundColor Gray
    flutter --version
    exit 0
}

Write-Host "Flutter n'est pas installé. Choisissez une méthode d'installation :" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Installation automatique (télécharge et installe Flutter)" -ForegroundColor Cyan
Write-Host "2. Vérifier si Flutter est installé ailleurs" -ForegroundColor Cyan
Write-Host "3. Afficher les instructions d'installation manuelle" -ForegroundColor Cyan
Write-Host ""
$choice = Read-Host "Votre choix (1/2/3)"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "Installation automatique de Flutter..." -ForegroundColor Green
    
    # Vérifier si Chocolatey est installé
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        Write-Host "Chocolatey détecté. Installation via Chocolatey..." -ForegroundColor Cyan
        choco install flutter -y
    } else {
        Write-Host ""
        Write-Host "Chocolatey n'est pas installé." -ForegroundColor Yellow
        Write-Host "Installation manuelle requise." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Étapes :" -ForegroundColor Cyan
        Write-Host "1. Téléchargez Flutter depuis : https://docs.flutter.dev/get-started/install/windows" -ForegroundColor White
        Write-Host "2. Extrayez dans C:\src\flutter" -ForegroundColor White
        Write-Host "3. Ajoutez C:\src\flutter\bin au PATH Windows" -ForegroundColor White
        Write-Host "4. Redémarrez PowerShell et exécutez 'flutter doctor'" -ForegroundColor White
    }
} elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "Recherche de Flutter..." -ForegroundColor Cyan
    
    $commonPaths = @(
        "$env:LOCALAPPDATA\flutter",
        "C:\src\flutter",
        "C:\flutter",
        "$env:USERPROFILE\flutter"
    )
    
    $found = $false
    foreach ($path in $commonPaths) {
        $flutterExe = Join-Path $path "bin\flutter.bat"
        if (Test-Path $flutterExe) {
            Write-Host "✅ Flutter trouvé dans : $path" -ForegroundColor Green
            Write-Host ""
            Write-Host "Pour l'ajouter au PATH, exécutez :" -ForegroundColor Yellow
            Write-Host "[Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$path\bin', [EnvironmentVariableTarget]::User)" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Puis redémarrez PowerShell." -ForegroundColor Yellow
            $found = $true
            break
        }
    }
    
    if (-not $found) {
        Write-Host "❌ Flutter non trouvé dans les emplacements courants." -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Instructions d'Installation" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📥 Étape 1 : Télécharger Flutter" -ForegroundColor Green
    Write-Host "   URL: https://docs.flutter.dev/get-started/install/windows" -ForegroundColor White
    Write-Host ""
    Write-Host "📦 Étape 2 : Extraire Flutter" -ForegroundColor Green
    Write-Host "   - Créez le dossier C:\src (s'il n'existe pas)" -ForegroundColor White
    Write-Host "   - Extrayez le fichier ZIP dans C:\src\flutter" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Étape 3 : Ajouter au PATH" -ForegroundColor Green
    Write-Host "   Méthode A (Interface) :" -ForegroundColor Cyan
    Write-Host "   - Win + R → sysdm.cpl → Onglet Avancé" -ForegroundColor White
    Write-Host "   - Variables d'environnement → Path → Modifier" -ForegroundColor White
    Write-Host "   - Ajouter : C:\src\flutter\bin" -ForegroundColor White
    Write-Host ""
    Write-Host "   Méthode B (PowerShell Admin) :" -ForegroundColor Cyan
    Write-Host "   [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';C:\src\flutter\bin', 'User')" -ForegroundColor White
    Write-Host ""
    Write-Host "✅ Étape 4 : Vérifier" -ForegroundColor Green
    Write-Host "   Redémarrez PowerShell puis : flutter doctor" -ForegroundColor White
    Write-Host ""
    Write-Host "📱 Alternative : Utiliser Android Studio" -ForegroundColor Yellow
    Write-Host "   - Installez Android Studio" -ForegroundColor White
    Write-Host "   - Installez le plugin Flutter" -ForegroundColor White
    Write-Host "   - Flutter sera installé automatiquement" -ForegroundColor White
}

Write-Host ""
Write-Host "Pour plus d'informations, consultez : mobile-app\INSTALLER_FLUTTER.md" -ForegroundColor Cyan


