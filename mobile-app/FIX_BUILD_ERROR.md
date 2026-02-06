# 🔧 Solution pour l'erreur "Accès refusé" lors du build Flutter

## Erreur rencontrée
```
Accès refusé.
Error: Unable to determine engine version...
FAILURE: Build failed with an exception.
Execution failed for task ':app:compileFlutterBuildDebug'.
```

## Solutions à essayer (dans l'ordre)

### 1. Nettoyer complètement le projet
```powershell
cd mobile-app
flutter clean
flutter pub get
```

### 2. Nettoyer le cache Gradle
```powershell
cd mobile-app\android
Remove-Item -Recurse -Force .gradle -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force app\build -ErrorAction SilentlyContinue
cd ..
```

### 3. Arrêter tous les processus Java/Gradle
```powershell
# Arrêter tous les processus Java
Get-Process -Name "java" -ErrorAction SilentlyContinue | Stop-Process -Force

# Arrêter tous les processus Gradle
Get-Process -Name "gradle*" -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 4. Vérifier les permissions
- Assurez-vous d'avoir les droits d'administration
- Vérifiez que les dossiers `build`, `.dart_tool`, `android\.gradle` ne sont pas en lecture seule

### 5. Désactiver temporairement l'antivirus
- Certains antivirus peuvent bloquer l'accès aux fichiers pendant la compilation
- Ajoutez une exception pour le dossier du projet

### 6. Réessayer avec des options différentes
```powershell
# Option 1: Build sans Gradle daemon
cd mobile-app
flutter build apk --debug --no-gradle-daemon

# Option 2: Build avec stacktrace
flutter run --verbose

# Option 3: Build en mode release (parfois plus stable)
flutter build apk --release
```

### 7. Vérifier l'espace disque
```powershell
# Vérifier l'espace disque disponible
Get-PSDrive C | Select-Object Used,Free
```

### 8. Réinitialiser Flutter
```powershell
flutter doctor -v
flutter upgrade
flutter pub cache repair
```

### 9. Solution alternative : Build via Android Studio
1. Ouvrir Android Studio
2. Ouvrir le projet : `mobile-app/android`
3. Build → Make Project
4. Run → Run 'app'

### 10. Vérifier les variables d'environnement
```powershell
# Vérifier JAVA_HOME
echo $env:JAVA_HOME

# Vérifier ANDROID_HOME
echo $env:ANDROID_HOME
```

## Solution recommandée (ordre d'exécution)

```powershell
# 1. Arrêter tous les processus
Get-Process -Name "java","gradle*" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Nettoyer complètement
cd "D:\logiciel et application\Mobility Health\mobile-app"
flutter clean
Remove-Item -Recurse -Force android\.gradle -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force android\app\build -ErrorAction SilentlyContinue

# 3. Récupérer les dépendances
flutter pub get

# 4. Réessayer
flutter run
```

## Si le problème persiste

1. **Redémarrer l'ordinateur** (libère tous les verrous de fichiers)
2. **Vérifier les logs détaillés** :
   ```powershell
   flutter run --verbose 2>&1 | Tee-Object -FilePath build_log.txt
   ```
3. **Créer un nouveau projet Flutter** et copier le code (dernier recours)

## Causes possibles

- ✅ Fichiers verrouillés par un processus Java/Gradle
- ✅ Permissions insuffisantes
- ✅ Antivirus bloquant l'accès
- ✅ Espace disque insuffisant
- ✅ Cache corrompu
- ✅ Problème avec le SDK Android

