# 🔧 Résolution de l'erreur d'installation ADB

## ❌ Erreur rencontrée

```
Error: ADB exited with exit code 1
adb.exe: failed to install D:\logiciel et application\Mobility Health\mobile-app\build\app\outputs\flutter-apk\app-debug.apk
```

## 🔍 Causes possibles

1. **Application déjà installée avec une signature différente**
2. **Pas assez d'espace sur l'appareil**
3. **L'appareil n'est pas correctement connecté**
4. **L'application est verrouillée ou en cours d'utilisation**
5. **Problème de permissions sur l'appareil**

## ✅ Solutions

### Solution 1 : Désinstaller l'application existante (Recommandé)

Si l'application est déjà installée avec une signature différente, vous devez la désinstaller d'abord :

```powershell
# Vérifier que l'appareil est connecté
adb devices

# Désinstaller l'application existante
adb uninstall com.example.mobility_health_mobile

# Ou avec le nom du package exact (vérifiez dans android/app/build.gradle)
adb uninstall mobility.health.mobile
```

**Puis relancer l'installation :**
```powershell
flutter run
```

### Solution 2 : Désinstaller manuellement depuis l'appareil

1. Sur votre appareil Android, allez dans **Paramètres** → **Applications**
2. Trouvez l'application "mobility_health_mobile" ou "Mobility Health"
3. Appuyez sur **Désinstaller**
4. Relancez `flutter run`

### Solution 3 : Vérifier la connexion ADB

```powershell
# Vérifier que l'appareil est bien connecté
adb devices

# Si l'appareil n'apparaît pas :
# 1. Vérifiez que le débogage USB est activé sur l'appareil
# 2. Autorisez l'ordinateur sur l'appareil (popup qui apparaît)
# 3. Redémarrez le serveur ADB
adb kill-server
adb start-server
adb devices
```

### Solution 4 : Nettoyer et reconstruire

```powershell
# Nettoyer le build
flutter clean

# Nettoyer les dépendances Gradle
cd android
.\gradlew clean
cd ..

# Reconstruire
flutter pub get
flutter run
```

### Solution 5 : Vérifier l'espace disponible

```powershell
# Vérifier l'espace disponible sur l'appareil
adb shell df -h

# Si l'espace est insuffisant, libérez de l'espace sur l'appareil
```

### Solution 6 : Installation forcée

```powershell
# Installer avec l'option -r (remplace l'application existante)
adb install -r build\app\outputs\flutter-apk\app-debug.apk

# Ou avec l'option -d (permet de downgrade)
adb install -r -d build\app\outputs\flutter-apk\app-debug.apk
```

### Solution 7 : Vérifier les permissions de l'appareil

1. Sur votre appareil Android :
   - Allez dans **Paramètres** → **Applications** → **Gestionnaire d'applications**
   - Trouvez "Services Google Play"
   - Activez toutes les permissions nécessaires

2. Vérifiez que le **débogage USB** est activé :
   - **Paramètres** → **Options développeur** → **Débogage USB** (activé)

### Solution 8 : Redémarrer ADB et l'appareil

```powershell
# Redémarrer ADB
adb kill-server
adb start-server

# Redémarrer l'appareil (via ADB)
adb reboot

# Attendre que l'appareil redémarre, puis :
adb devices
flutter run
```

## 🎯 Solution rapide (essayer dans l'ordre)

1. **Désinstaller l'application existante :**
   ```powershell
   adb uninstall mobility.health.mobile
   ```

2. **Nettoyer et reconstruire :**
   ```powershell
   flutter clean
   flutter pub get
   flutter run
   ```

3. **Si ça ne fonctionne toujours pas, installer manuellement :**
   ```powershell
   adb install -r build\app\outputs\flutter-apk\app-debug.apk
   ```

## 🔍 Vérifier le nom du package

Pour trouver le nom exact du package, vérifiez dans `android/app/build.gradle` :

```gradle
android {
    namespace "mobility.health.mobile"  // ← C'est le nom du package
    // ou
    applicationId "mobility.health.mobile"  // ← Ou ici
}
```

Puis désinstallez avec ce nom exact :
```powershell
adb uninstall mobility.health.mobile
```

## 📱 Vérifier que l'appareil est prêt

```powershell
# Vérifier la connexion
adb devices

# Vous devriez voir quelque chose comme :
# List of devices attached
# SM A156U1    device
```

Si vous voyez `unauthorized`, vous devez autoriser l'ordinateur sur l'appareil.

## ⚠️ Notes importantes

1. **Le débogage USB doit être activé** sur l'appareil
2. **Autorisez l'ordinateur** quand la popup apparaît sur l'appareil
3. **Utilisez un câble USB de qualité** (certains câbles ne supportent que la charge)
4. **Vérifiez les pilotes USB** si l'appareil n'est pas reconnu

## 🐛 Si rien ne fonctionne

1. **Réinstaller les pilotes USB Android** :
   - Téléchargez Android USB Driver depuis le site officiel
   - Installez les pilotes pour votre appareil

2. **Utiliser le mode Wi-Fi ADB** :
   ```powershell
   # Connecter d'abord en USB, puis :
   adb tcpip 5555
   adb connect <IP_DE_L_APPAREIL>:5555
   ```

3. **Vérifier les logs détaillés** :
   ```powershell
   flutter run -v
   ```

## 📞 Besoin d'aide supplémentaire ?

Consultez aussi :
- [Flutter Troubleshooting](https://docs.flutter.dev/troubleshooting)
- [Android Debug Bridge (ADB)](https://developer.android.com/studio/command-line/adb)

