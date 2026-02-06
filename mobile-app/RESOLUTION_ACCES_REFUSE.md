# 🔧 Résolution de l'erreur "Accès refusé" - Flutter Build

## ✅ Actions déjà effectuées

1. ✅ Nettoyage complet du projet (`flutter clean`)
2. ✅ Nettoyage des caches Gradle
3. ✅ Vérification du chemin Flutter SDK (correct: `C:\src\flutter`)
4. ✅ Récupération des dépendances (`flutter pub get`)
5. ✅ Vérification de `local.properties` (configuration correcte)

## 🔍 Diagnostic

L'erreur "Accès refusé" (Access denied) se produit généralement lorsque :
- Des fichiers sont verrouillés par un processus Java/Gradle
- L'antivirus bloque l'accès aux fichiers
- Les permissions sur le dossier Flutter SDK sont insuffisantes
- Le cache Gradle est corrompu

## 🛠️ Solutions à essayer (dans l'ordre)

### Solution 1 : Build sans Gradle Daemon

Le daemon Gradle peut parfois verrouiller des fichiers. Essayez de build sans lui :

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app"
flutter build apk --debug --no-gradle-daemon
```

### Solution 2 : Vérifier les permissions du dossier Flutter

```powershell
# Vérifier les permissions
Get-Acl "C:\src\flutter" | Format-List

# Si nécessaire, donner les permissions complètes (exécuter en tant qu'administrateur)
icacls "C:\src\flutter" /grant "${env:USERNAME}:(OI)(CI)F" /T
```

### Solution 3 : Désactiver temporairement l'antivirus

1. Désactivez temporairement votre antivirus
2. Ajoutez une exception pour :
   - `C:\src\flutter`
   - `D:\logiciel et application\Mobility Health\mobile-app`
   - `C:\Users\HP\.gradle`

### Solution 4 : Nettoyer complètement et reconstruire

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app"

# Arrêter tous les processus
Get-Process -Name "java","gradle*","dart" -ErrorAction SilentlyContinue | Stop-Process -Force

# Nettoyer Flutter
flutter clean

# Nettoyer Gradle
Remove-Item -Recurse -Force android\.gradle -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force android\app\build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force android\build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches" -ErrorAction SilentlyContinue

# Récupérer les dépendances
flutter pub get

# Essayer de build
flutter build apk --debug
```

### Solution 5 : Vérifier l'espace disque

```powershell
Get-PSDrive C | Select-Object Used,Free
```

Assurez-vous d'avoir au moins 5-10 Go d'espace libre.

### Solution 6 : Vérifier Flutter Doctor

```powershell
flutter doctor -v
```

Vérifiez qu'il n'y a pas d'erreurs critiques (notamment pour Android toolchain).

### Solution 7 : Build avec stacktrace détaillé

Pour obtenir plus d'informations sur l'erreur :

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app"
flutter build apk --debug --verbose 2>&1 | Tee-Object -FilePath build_log.txt
```

Ensuite, examinez le fichier `build_log.txt` pour voir où exactement l'erreur se produit.

### Solution 8 : Utiliser Android Studio

Parfois, Android Studio gère mieux les permissions :

1. Ouvrez Android Studio
2. File → Open → Sélectionnez `mobile-app/android`
3. Build → Make Project
4. Run → Run 'app'

## 🎯 Solution recommandée (ordre d'exécution)

```powershell
# 1. Arrêter tous les processus
Get-Process -Name "java","gradle*","dart" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Nettoyer complètement
cd "D:\logiciel et application\Mobility Health\mobile-app"
flutter clean
Remove-Item -Recurse -Force android\.gradle -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force android\app\build -ErrorAction SilentlyContinue

# 3. Récupérer les dépendances
flutter pub get

# 4. Build sans daemon (plus lent mais plus stable)
flutter build apk --debug --no-gradle-daemon
```

## 🔍 Vérifications supplémentaires

### Vérifier que Flutter est accessible

```powershell
# Tester l'accès au binaire Flutter
Test-Path "C:\src\flutter\bin\flutter.bat"
C:\src\flutter\bin\flutter.bat --version
```

### Vérifier les variables d'environnement

```powershell
echo $env:JAVA_HOME
echo $env:ANDROID_HOME
echo $env:PATH | Select-String "flutter"
```

### Vérifier les logs Gradle

Les logs Gradle peuvent être trouvés dans :
- `android\.gradle\daemon\<version>\daemon-*.out.log`

## ⚠️ Si le problème persiste

1. **Redémarrer l'ordinateur** - Cela libère tous les verrous de fichiers
2. **Vérifier les logs détaillés** avec `--verbose`
3. **Créer un nouveau projet Flutter** et copier le code (dernier recours)

## 📝 Notes importantes

- L'erreur "Accès refusé" est souvent liée à des processus qui verrouillent des fichiers
- L'antivirus Windows Defender peut parfois bloquer l'accès
- Assurez-vous d'exécuter PowerShell en tant qu'administrateur si nécessaire
- Le build sans daemon est plus lent mais évite souvent les problèmes de verrous

## 🆘 Support

Si aucune de ces solutions ne fonctionne, collectez les informations suivantes :

```powershell
# Informations système
flutter doctor -v > flutter_doctor.txt
Get-Content android\local.properties > local_properties.txt
Get-Content android\gradle.properties > gradle_properties.txt

# Logs de build
flutter build apk --debug --verbose 2>&1 | Tee-Object -FilePath build_error_log.txt
```

Ensuite, partagez ces fichiers pour un diagnostic plus approfondi.








