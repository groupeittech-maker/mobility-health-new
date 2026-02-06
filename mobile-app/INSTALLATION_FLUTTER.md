# Installation de Flutter et Lancement de l'Application

## 📦 Étape 1 : Installer Flutter

### Windows

1. **Télécharger Flutter** :
   - Allez sur : https://flutter.dev/docs/get-started/install/windows
   - Téléchargez le SDK Flutter
   - Extrayez l'archive dans un dossier (ex: `C:\src\flutter`)

2. **Ajouter Flutter au PATH** :
   - Ouvrez "Variables d'environnement" dans Windows
   - Ajoutez `C:\src\flutter\bin` au PATH
   - Redémarrez PowerShell/Terminal

3. **Vérifier l'installation** :
   ```powershell
   flutter doctor
   ```

4. **Installer les dépendances** :
   - Android Studio (pour Android)
   - Visual Studio (pour Windows desktop)
   - Suivez les instructions de `flutter doctor`

### Alternative : Utiliser Flutter via Android Studio

1. Installez Android Studio
2. Installez le plugin Flutter dans Android Studio
3. Flutter sera installé automatiquement

## 🚀 Étape 2 : Lancer l'Application

### Vérifications Préalables

1. **Backend démarré** :
   ```bash
   # Depuis la racine du projet
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Fichier .env configuré** :
   - Vérifiez que `mobile-app/.env` contient la bonne URL
   - Pour appareil physique : `http://172.16.202.81:8000/api/v1`

### Lancer l'Application

1. **Ouvrir un terminal dans `mobile-app`**

2. **Installer les dépendances** :
   ```bash
   flutter pub get
   ```

3. **Vérifier les appareils** :
   ```bash
   flutter devices
   ```

4. **Lancer l'application** :
   ```bash
   flutter run
   ```

## 📱 Options de Développement

### Android Studio (Recommandé)

1. Ouvrez Android Studio
2. File → Open → Sélectionnez le dossier `mobile-app`
3. Attendez que Flutter configure le projet
4. Cliquez sur le bouton "Run" (▶️)

### VS Code

1. Installez l'extension "Flutter" dans VS Code
2. Ouvrez le dossier `mobile-app`
3. Appuyez sur F5 ou cliquez sur "Run and Debug"

### Terminal

```bash
cd mobile-app
flutter run
```

## 🔧 Dépannage

### Flutter non reconnu

**Solution** : Ajoutez Flutter au PATH ou utilisez le chemin complet :
```powershell
C:\src\flutter\bin\flutter.exe doctor
```

### Aucun appareil trouvé

**Pour Android** :
1. Installez Android Studio
2. Créez un émulateur Android (AVD Manager)
3. Démarrez l'émulateur
4. Relancez `flutter devices`

**Pour iOS** (Mac uniquement) :
1. Installez Xcode
2. Ouvrez Xcode et acceptez les licences
3. Créez un simulateur iOS

### Erreur de connexion API

Vérifiez que :
1. Le backend est démarré avec `--host 0.0.0.0`
2. L'URL dans `.env` est correcte
3. Le firewall autorise le port 8000

## 📚 Ressources

- Documentation Flutter : https://flutter.dev/docs
- Guide d'installation : https://flutter.dev/docs/get-started/install


