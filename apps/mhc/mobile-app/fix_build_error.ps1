# Script de correction pour l'erreur "Accès refusé" Flutter Build
# Usage: .\fix_build_error.ps1

Write-Host "🔧 Correction de l'erreur de build Flutter..." -ForegroundColor Cyan
Write-Host ""

# Étape 1: Arrêter tous les processus Java/Gradle
Write-Host "1️⃣ Arrêt des processus Java/Gradle..." -ForegroundColor Yellow
Get-Process -Name "java" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "gradle*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "dart" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "   ✅ Processus arrêtés" -ForegroundColor Green

# Étape 2: Trouver le chemin Flutter correct
Write-Host ""
Write-Host "2️⃣ Recherche du chemin Flutter..." -ForegroundColor Yellow
$flutterPath = $null

# Méthode 1: Vérifier si flutter est dans PATH
try {
    $flutterCheck = flutter --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $flutterWhich = (Get-Command flutter -ErrorAction SilentlyContinue).Source
        if ($flutterWhich) {
            $flutterPath = Split-Path (Split-Path $flutterWhich -Parent) -Parent
            Write-Host "   ✅ Flutter trouvé dans PATH: $flutterPath" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "   ⚠️ Flutter non trouvé dans PATH" -ForegroundColor Yellow
}

# Méthode 2: Vérifier les emplacements communs
if (-not $flutterPath) {
    $commonPaths = @(
        "C:\src\flutter",
        "C:\flutter",
        "$env:USERPROFILE\flutter",
        "$env:LOCALAPPDATA\flutter",
        "C:\Program Files\flutter"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path "$path\bin\flutter.bat") {
            $flutterPath = $path
            Write-Host "   ✅ Flutter trouvé: $flutterPath" -ForegroundColor Green
            break
        }
    }
}

# Méthode 3: Demander à l'utilisateur
if (-not $flutterPath) {
    Write-Host "   ⚠️ Flutter non trouvé automatiquement" -ForegroundColor Yellow
    $userPath = Read-Host "   Entrez le chemin vers Flutter (ex: C:\src\flutter)"
    if (Test-Path "$userPath\bin\flutter.bat") {
        $flutterPath = $userPath
        Write-Host "   ✅ Chemin validé: $flutterPath" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Chemin invalide. Veuillez installer Flutter ou corriger le chemin." -ForegroundColor Red
        exit 1
    }
}

# Étape 3: Nettoyer complètement le projet
Write-Host ""
Write-Host "3️⃣ Nettoyage du projet..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot"

# Nettoyer Flutter
Write-Host "   Nettoyage Flutter..." -ForegroundColor Gray
flutter clean 2>&1 | Out-Null

# Nettoyer les caches Gradle
Write-Host "   Nettoyage cache Gradle..." -ForegroundColor Gray
if (Test-Path "android\.gradle") {
    Remove-Item -Recurse -Force "android\.gradle" -ErrorAction SilentlyContinue
}
if (Test-Path "android\app\build") {
    Remove-Item -Recurse -Force "android\app\build" -ErrorAction SilentlyContinue
}
if (Test-Path "android\build") {
    Remove-Item -Recurse -Force "android\build" -ErrorAction SilentlyContinue
}

# Nettoyer les caches Dart
Write-Host "   Nettoyage cache Dart..." -ForegroundColor Gray
if (Test-Path ".dart_tool") {
    Remove-Item -Recurse -Force ".dart_tool" -ErrorAction SilentlyContinue
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
}

Write-Host "   ✅ Nettoyage terminé" -ForegroundColor Green

# Étape 4: Mettre à jour local.properties
Write-Host ""
Write-Host "4️⃣ Mise à jour de local.properties..." -ForegroundColor Yellow
$localPropsPath = "android\local.properties"

# Normaliser le chemin Flutter pour Windows
$flutterPathNormalized = $flutterPath -replace '\\', '\\'

# Lire le fichier existant ou créer un nouveau
$props = @{}
if (Test-Path $localPropsPath) {
    Get-Content $localPropsPath | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $props[$matches[1]] = $matches[2]
        }
    }
}

# Mettre à jour le chemin Flutter
$props['flutter.sdk'] = $flutterPathNormalized

# S'assurer que sdk.dir existe
if (-not $props.ContainsKey('sdk.dir')) {
    $androidSdkPath = $env:ANDROID_HOME
    if (-not $androidSdkPath) {
        $androidSdkPath = "$env:LOCALAPPDATA\Android\Sdk"
    }
    if (Test-Path $androidSdkPath) {
        $props['sdk.dir'] = $androidSdkPath -replace '\\', '\\'
    }
}

# Écrire le fichier
$content = @()
$content += "sdk.dir=$($props['sdk.dir'])"
$content += "flutter.sdk=$($props['flutter.sdk'])"
$content += "flutter.buildMode=debug"
$content += "flutter.versionName=1.0.0"
$content += "flutter.versionCode=1"

$content | Out-File -FilePath $localPropsPath -Encoding ASCII -NoNewline
Write-Host "   ✅ local.properties mis à jour avec: $flutterPathNormalized" -ForegroundColor Green

# Étape 5: Récupérer les dépendances
Write-Host ""
Write-Host "5️⃣ Récupération des dépendances..." -ForegroundColor Yellow
flutter pub get
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Erreur lors de la récupération des dépendances" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Dépendances récupérées" -ForegroundColor Green

# Étape 6: Vérifier Flutter Doctor
Write-Host ""
Write-Host "6️⃣ Vérification de l'environnement Flutter..." -ForegroundColor Yellow
flutter doctor -v
Write-Host ""

# Étape 7: Instructions finales
Write-Host ""
Write-Host "✅ Correction terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Prochaines étapes:" -ForegroundColor Cyan
Write-Host "   1. Vérifiez que Flutter Doctor ne montre pas d'erreurs critiques" -ForegroundColor White
Write-Host "   2. Essayez de lancer l'application:" -ForegroundColor White
Write-Host "      flutter run" -ForegroundColor Gray
Write-Host ""
Write-Host "   Si le problème persiste, essayez:" -ForegroundColor Yellow
Write-Host "      flutter run --verbose" -ForegroundColor Gray
Write-Host ""








