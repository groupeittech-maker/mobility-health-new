# 🚀 Lancer l'Application Sans Flutter (Alternative)

Si vous ne pouvez pas installer Flutter pour le moment, voici des alternatives :

## Option 1 : Utiliser Android Studio (Recommandé)

### Avantages
- ✅ Pas besoin de configurer Flutter manuellement
- ✅ Installation automatique de Flutter via le plugin
- ✅ Interface graphique intuitive
- ✅ Gestion automatique des émulateurs

### Étapes

1. **Télécharger Android Studio**
   - https://developer.android.com/studio
   - Installez-le avec les options par défaut

2. **Installer le Plugin Flutter**
   - Ouvrez Android Studio
   - File → Settings → Plugins (ou Ctrl+Alt+S)
   - Cherchez "Flutter" dans la recherche
   - Cliquez sur "Install"
   - Il vous proposera d'installer le plugin Dart aussi → Acceptez
   - Redémarrez Android Studio

3. **Ouvrir le Projet**
   - File → Open
   - Sélectionnez le dossier `mobile-app`
   - Android Studio détectera automatiquement que c'est un projet Flutter

4. **Configurer l'Émulateur**
   - Tools → Device Manager
   - Cliquez sur "Create Device"
   - Choisissez un appareil (ex: Pixel 5)
   - Téléchargez une image système
   - Cliquez sur "Finish"

5. **Lancer l'Application**
   - Cliquez sur le bouton vert "Run" (▶️) en haut
   - Ou appuyez sur Shift+F10
   - L'application se lancera dans l'émulateur

## Option 2 : Utiliser VS Code

### Prérequis
- VS Code installé

### Étapes

1. **Installer les Extensions**
   - Ouvrez VS Code
   - Extensions (Ctrl+Shift+X)
   - Installez "Flutter"
   - Installez "Dart" (sera suggéré automatiquement)

2. **Ouvrir le Projet**
   - File → Open Folder
   - Sélectionnez le dossier `mobile-app`

3. **Configurer Flutter**
   - VS Code vous demandera d'installer Flutter
   - Suivez les instructions

4. **Lancer**
   - Appuyez sur F5
   - Ou utilisez la commande palette (Ctrl+Shift+P) → "Flutter: Run"

## Option 3 : Utiliser l'App Web Temporairement

En attendant d'installer Flutter, vous pouvez tester l'API avec le frontend web :

1. **Démarrer le backend** (si pas déjà fait)
   ```powershell
   cd ..
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Ouvrir le frontend web**
   - Ouvrez `frontend-simple/index.html` dans un navigateur
   - Ou utilisez un serveur local :
   ```powershell
   cd frontend-simple
   python -m http.server 3000
   ```
   - Puis ouvrez : http://localhost:3000

## 📝 Checklist Avant de Lancer

- [ ] Backend démarré sur `0.0.0.0:8000`
- [ ] Fichier `.env` configuré dans `mobile-app/`
- [ ] Flutter installé OU Android Studio installé
- [ ] Émulateur Android créé et démarré (ou appareil connecté)

## ⚠️ Important

Pour tester l'application mobile complètement, vous devrez installer Flutter. Mais Android Studio est la méthode la plus simple car il gère tout automatiquement.

## 🆘 Besoin d'Aide ?

1. Consultez `INSTALLER_FLUTTER.md` pour un guide détaillé
2. Exécutez `.\install_flutter.ps1` pour un assistant d'installation
3. Utilisez Android Studio si vous préférez une interface graphique


