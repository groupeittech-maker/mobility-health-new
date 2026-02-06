@echo off
REM Script pour lancer l'application mobile Flutter
REM Usage: lancer.bat

echo ========================================
echo   Lancement de l'application mobile
echo ========================================
echo.

REM Vérifier que nous sommes dans le bon répertoire
if not exist "pubspec.yaml" (
    echo ERREUR: Vous devez etre dans le dossier mobile-app
    echo Changez de repertoire avec: cd mobile-app
    pause
    exit /b 1
)

echo Verification des appareils disponibles...
flutter devices
echo.

echo Lancement de l'application...
flutter run

pause

