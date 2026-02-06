# Guide d'Installation de Flutter pour Windows

## 🚀 Installation Rapide

### Option 1 : Installation Automatique (Recommandé)

1. **Télécharger Flutter SDK**
   - Allez sur : https://docs.flutter.dev/get-started/install/windows
   - Cliquez sur "Download Flutter SDK"
   - Téléchargez le fichier ZIP

2. **Extraire Flutter**
   - Créez un dossier `C:\src` (ou utilisez un autre emplacement)
   - Extrayez le fichier ZIP dans `C:\src\flutter`

3. **Ajouter Flutter au PATH**
   
   **Méthode A : Via l'interface Windows**
   - Appuyez sur `Win + R`, tapez `sysdm.cpl` et appuyez sur Entrée
   - Allez dans l'onglet "Avancé"
   - Cliquez sur "Variables d'environnement"
   - Dans "Variables système", sélectionnez "Path" et cliquez sur "Modifier"
   - Cliquez sur "Nouveau" et ajoutez : `C:\src\flutter\bin`
   - Cliquez sur "OK" partout
   - **Redémarrez PowerShell/Terminal**

   **Méthode B : Via PowerShell (Administrateur)**
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\src\flutter\bin", [EnvironmentVariableTarget]::Machine)
   ```
   Redémarrez PowerShell après.

4. **Vérifier l'installation**
   ```powershell
   flutter doctor
   ```

### Option 2 : Installation via Android Studio (Plus Simple)

1. **Installer Android Studio**
   - Téléchargez depuis : https://developer.android.com/studio
   - Installez Android Studio avec les options par défaut

2. **Installer le Plugin Flutter**
   - Ouvrez Android Studio
   - File → Settings → Plugins
   - Cherchez "Flutter" et installez-le
   - Il installera automatiquement le Dart SDK et Flutter

3. **Vérifier l'installation**
   - Ouvrez Android Studio
   - File → New → New Flutter Project
   - Si Flutter est détecté, c'est bon !

### Option 3 : Installation via Chocolatey (Rapide)

Si vous avez Chocolatey installé :

```powershell
# Ouvrir PowerShell en Administrateur
choco install flutter
```

Puis redémarrer PowerShell et vérifier :
```powershell
flutter doctor
```

## ✅ Vérification

Après l'installation, testez :

```powershell
# Vérifier la version
flutter --version

# Vérifier l'état de l'installation
flutter doctor
```

## 🔧 Configuration

### Installer les Dépendances Manquantes

`flutter doctor` vous dira ce qui manque. En général, vous aurez besoin de :

1. **Android Studio** (pour Android)
   - Installez Android Studio
   - Ouvrez-le et acceptez les licences
   - Installez les SDK Android nécessaires

2. **Visual Studio** (pour Windows desktop)
   - Installez Visual Studio Community
   - Cochez "Développement Desktop en C++" lors de l'installation

### Accepter les Licences Android

```powershell
flutter doctor --android-licenses
```

## 📱 Créer un Émulateur Android

1. Ouvrez Android Studio
2. Tools → Device Manager
3. Cliquez sur "Create Device"
4. Choisissez un appareil (ex: Pixel 5)
5. Téléchargez une image système (ex: API 33)
6. Cliquez sur "Finish"

## 🚀 Alternative : Utiliser Android Studio Directement

Si vous avez des problèmes avec Flutter en ligne de commande :

1. Ouvrez Android Studio
2. File → Open → Sélectionnez le dossier `mobile-app`
3. Android Studio détectera automatiquement le projet Flutter
4. Cliquez sur le bouton "Run" (▶️) pour lancer l'application

## 🐛 Dépannage

### Flutter toujours non reconnu après installation

1. Vérifiez que vous avez bien redémarré PowerShell/Terminal
2. Vérifiez le PATH :
   ```powershell
   $env:PATH -split ';' | Select-String flutter
   ```
3. Testez avec le chemin complet :
   ```powershell
   C:\src\flutter\bin\flutter.bat doctor
   ```

### Erreur : "Android license not accepted"

```powershell
flutter doctor --android-licenses
# Acceptez toutes les licences en tapant 'y'
```

### Erreur : "No devices found"

1. Démarrez un émulateur Android depuis Android Studio
2. Ou connectez un appareil Android avec USB Debugging activé

## 📚 Ressources

- Documentation officielle : https://docs.flutter.dev/get-started/install/windows
- Android Studio : https://developer.android.com/studio
- Guide de démarrage : https://docs.flutter.dev/get-started/editor

## ⚡ Solution Rapide pour Démarrer Maintenant

Si vous voulez tester rapidement sans installer Flutter :

1. **Installez Android Studio** (environ 1 GB)
2. **Installez le plugin Flutter** dans Android Studio
3. **Ouvrez le projet** dans Android Studio
4. **Cliquez sur Run**

C'est la méthode la plus simple pour commencer !


