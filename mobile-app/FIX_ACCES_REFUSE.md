# 🔧 Résolution rapide : Erreur "Accès refusé" Flutter

## ⚡ Solution rapide (1 commande)

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app"
.\quick_fix_build.ps1
```

## 🔍 Diagnostic de l'erreur

L'erreur `Accès refusé. Error: Unable to determine engine version` indique généralement :
- Des fichiers Flutter sont verrouillés par un processus
- Problème de permissions sur `C:\src\flutter`
- Cache Flutter corrompu
- Antivirus bloquant l'accès

## ✅ Solutions étape par étape

### Solution 1 : Script automatique (RECOMMANDÉ)

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app"
.\quick_fix_build.ps1
```

### Solution 2 : Nettoyage manuel

```powershell
# 1. Arrêter tous les processus
Get-Process -Name "java","gradle*","dart","flutter" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Nettoyer Flutter
cd "D:\logiciel et application\Mobility Health\mobile-app"
flutter clean

# 3. Nettoyer les caches
Remove-Item -Recurse -Force android\.gradle -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force android\app\build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .dart_tool -ErrorAction SilentlyContinue

# 4. Récupérer les dépendances
flutter pub get

# 5. Build sans daemon
flutter build apk --debug --no-gradle-daemon
```

### Solution 3 : Vérifier les permissions Flutter

```powershell
# Vérifier les permissions
Get-Acl "C:\src\flutter" | Format-List

# Donner les permissions complètes (exécuter en tant qu'administrateur)
icacls "C:\src\flutter" /grant "${env:USERNAME}:(OI)(CI)F" /T
```

### Solution 4 : Réparer le cache Flutter

```powershell
flutter pub cache repair
flutter doctor -v
```

### Solution 5 : Vérifier l'espace disque

```powershell
Get-PSDrive C | Select-Object Used,Free
```

Assurez-vous d'avoir au moins **5-10 Go** d'espace libre.

## 🚨 Si rien ne fonctionne

1. **Redémarrer l'ordinateur** (libère tous les verrous)
2. **Désactiver temporairement l'antivirus**
3. **Exécuter PowerShell en tant qu'administrateur**
4. **Vérifier Flutter Doctor** :
   ```powershell
   flutter doctor -v
   ```

## 📝 Logs détaillés

Pour obtenir plus d'informations sur l'erreur :

```powershell
flutter run --verbose 2>&1 | Tee-Object -FilePath build_log.txt
```

Ensuite, examinez `build_log.txt` pour voir où exactement l'erreur se produit.
