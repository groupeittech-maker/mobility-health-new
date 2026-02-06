# Script pour corriger le problème de version Java
# Usage: .\CORRIGER_JAVA.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Correction du Problème Java" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier la version Java actuelle
Write-Host "Version Java actuelle:" -ForegroundColor Yellow
java -version
Write-Host ""

# Chercher Java 17 dans Android Studio
$androidStudioJava = "C:\Program Files\Android\Android Studio\jbr"
if (Test-Path $androidStudioJava) {
    Write-Host "✅ Java 17 trouvé dans Android Studio!" -ForegroundColor Green
    Write-Host "Chemin: $androidStudioJava" -ForegroundColor White
    
    # Vérifier la version
    $javaExe = Join-Path $androidStudioJava "bin\java.exe"
    if (Test-Path $javaExe) {
        $version = & $javaExe -version 2>&1 | Select-Object -First 1
        Write-Host "Version: $version" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "Configuration de Gradle pour utiliser Java 17..." -ForegroundColor Yellow
    
    # Mettre à jour gradle.properties
    $gradleProps = "android\gradle.properties"
    if (Test-Path $gradleProps) {
        $content = Get-Content $gradleProps -Raw
        
        # Vérifier si la ligne existe déjà
        if ($content -notmatch "org\.gradle\.java\.home") {
            # Ajouter la configuration
            $content += "`n# Configuration Java 17`n"
            $content += "org.gradle.java.home=$androidStudioJava`n"
            
            Set-Content -Path $gradleProps -Value $content -NoNewline
            Write-Host "✅ gradle.properties mis à jour!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  La configuration Java existe déjà dans gradle.properties" -ForegroundColor Yellow
            Write-Host "Vérifiez que le chemin est correct:" -ForegroundColor Yellow
            Get-Content $gradleProps | Select-String "java.home"
        }
    }
    
    Write-Host ""
    Write-Host "Prochaines étapes:" -ForegroundColor Cyan
    Write-Host "1. Nettoyer le projet: flutter clean" -ForegroundColor White
    Write-Host "2. Relancer: flutter run" -ForegroundColor White
} else {
    Write-Host "❌ Java 17 non trouvé dans Android Studio" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "1. Installer Android Studio (inclut Java 17)" -ForegroundColor White
    Write-Host "   https://developer.android.com/studio" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Installer Java 17 séparément:" -ForegroundColor White
    Write-Host "   - OpenJDK: https://adoptium.net/temurin/releases/?version=17" -ForegroundColor Gray
    Write-Host "   - Oracle JDK: https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Après installation, configurez JAVA_HOME:" -ForegroundColor White
    Write-Host "   [System.Environment]::SetEnvironmentVariable('JAVA_HOME', 'C:\Program Files\Java\jdk-17', 'Machine')" -ForegroundColor Gray
}

