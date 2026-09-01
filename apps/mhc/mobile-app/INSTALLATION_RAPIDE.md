# 🚀 Installation Rapide de Flutter - Guide Pas à Pas

## 📥 Étape 1 : Télécharger Flutter

1. **Allez sur le site officiel** :
   - https://docs.flutter.dev/get-started/install/windows
   - Ou directement : https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.5-stable.zip

2. **Téléchargez le fichier ZIP** (environ 1.5 GB)
   - Sauvegardez-le dans votre dossier Téléchargements

## 📦 Étape 2 : Extraire Flutter

1. **Créez le dossier** `C:\src` (s'il n'existe pas)
   - Ouvrez l'Explorateur de fichiers
   - Allez dans `C:\`
   - Clic droit → Nouveau → Dossier
   - Nommez-le `src`

2. **Extrayez Flutter**
   - Ouvrez le fichier ZIP téléchargé
   - Extrayez tout le contenu dans `C:\src\flutter`
   - Vous devriez avoir : `C:\src\flutter\bin\flutter.bat`

## 🔧 Étape 3 : Ajouter Flutter au PATH

### Méthode Simple (Interface Windows)

1. **Ouvrir les Variables d'Environnement** :
   - Appuyez sur `Win + R`
   - Tapez : `sysdm.cpl`
   - Appuyez sur Entrée

2. **Modifier le PATH** :
   - Cliquez sur l'onglet **"Avancé"**
   - Cliquez sur **"Variables d'environnement"**
   - Dans la section **"Variables système"**, trouvez **"Path"**
   - Sélectionnez **"Path"** et cliquez sur **"Modifier"**
   - Cliquez sur **"Nouveau"**
   - Tapez : `C:\src\flutter\bin`
   - Cliquez sur **"OK"** partout

3. **Redémarrer PowerShell/Terminal**
   - Fermez tous les PowerShell/terminaux ouverts
   - Ouvrez un nouveau PowerShell
   - Testez : `flutter --version`

### Méthode PowerShell (Alternative)

Ouvrez PowerShell en **Administrateur** (clic droit → Exécuter en tant qu'administrateur) :

```powershell
# Ajouter Flutter au PATH utilisateur
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\src\flutter\bin",
    "User"
)
```

Puis **redémarrez PowerShell**.

## ✅ Étape 4 : Vérifier l'Installation

Ouvrez un **nouveau** PowerShell et exécutez :

```powershell
flutter --version
```

Vous devriez voir quelque chose comme :
```
Flutter 3.24.5 • channel stable • https://github.com/flutter/flutter.git
```

## 🏥 Étape 5 : Vérifier l'Environnement

Exécutez :

```powershell
flutter doctor
```

Cela vous montrera ce qui est installé et ce qui manque.

## 📱 Étape 6 : Configurer Android (Recommandé)

1. **Installer Android Studio**
   - Téléchargez : https://developer.android.com/studio
   - Installez avec les options par défaut

2. **Configurer Android dans Flutter**
   ```powershell
   flutter doctor --android-licenses
   ```
   - Acceptez toutes les licences (tapez `y` pour chaque)

3. **Créer un émulateur Android**
   - Ouvrez Android Studio
   - Tools → Device Manager
   - Create Device
   - Choisissez un appareil (ex: Pixel 5)
   - Téléchargez une image système
   - Finish

## 🚀 Étape 7 : Lancer l'Application

Maintenant vous pouvez lancer l'application mobile :

```powershell
cd mobile-app
flutter pub get
flutter devices    # Voir les appareils disponibles
flutter run        # Lancer l'application
```

## ⚡ Méthode Alternative : Utiliser Android Studio Directement

Si vous préférez une interface graphique :

1. Installez Android Studio
2. Installez le plugin Flutter dans Android Studio
3. Ouvrez le dossier `mobile-app` dans Android Studio
4. Cliquez sur Run (▶️)

C'est tout ! Flutter sera installé automatiquement via le plugin.

## 🐛 Dépannage

### Flutter non reconnu après installation

1. Vérifiez que vous avez bien redémarré PowerShell
2. Testez avec le chemin complet :
   ```powershell
   C:\src\flutter\bin\flutter.bat --version
   ```
3. Vérifiez le PATH :
   ```powershell
   $env:PATH -split ';' | Select-String flutter
   ```

### Erreur "Android license not accepted"

```powershell
flutter doctor --android-licenses
# Acceptez toutes les licences (tapez 'y')
```

### Pas d'appareil disponible

1. Démarrez un émulateur Android depuis Android Studio
2. Ou connectez un appareil Android avec USB Debugging activé

## 📚 Ressources

- Documentation officielle : https://docs.flutter.dev/get-started/install/windows
- Android Studio : https://developer.android.com/studio


