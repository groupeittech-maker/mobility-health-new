# 🚀 Guide Rapide pour Lancer l'Application

## ⚡ Démarrage Rapide (3 étapes)

### 1️⃣ Démarrer le Backend

Ouvrez un terminal dans la **racine du projet** et exécutez :

```powershell
# Windows
.\scripts\start_backend.ps1

# Ou manuellement
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

⚠️ **Important** : Utilisez `--host 0.0.0.0` (pas `localhost`) pour que l'API soit accessible depuis votre appareil mobile.

### 2️⃣ Vérifier le Fichier .env

Dans `mobile-app/.env`, vérifiez que l'URL est correcte :

```env
API_BASE_URL=http://172.16.202.81:8000/api/v1
```

**Trouver votre IP** :
```powershell
ipconfig
# Cherchez "IPv4" dans la section de votre carte réseau WiFi
```

### 3️⃣ Lancer l'Application Flutter

Ouvrez un terminal dans `mobile-app` :

```bash
# Installer les dépendances (première fois)
flutter pub get

# Lancer l'application
flutter run
```

## 📱 Si Flutter n'est pas Installé

### Option A : Installer Flutter

1. Téléchargez depuis : https://flutter.dev/docs/get-started/install/windows
2. Extrayez dans `C:\src\flutter`
3. Ajoutez `C:\src\flutter\bin` au PATH
4. Redémarrez le terminal

### Option B : Utiliser Android Studio

1. Installez Android Studio
2. Installez le plugin Flutter
3. Ouvrez le projet dans Android Studio
4. Cliquez sur "Run"

## ✅ Vérifications

Avant de lancer, vérifiez :

- [ ] Backend démarré sur `0.0.0.0:8000`
- [ ] Fichier `.env` avec la bonne IP
- [ ] Flutter installé (`flutter doctor`)
- [ ] Appareil/émulateur disponible (`flutter devices`)

## 🐛 Problème : "Not Found" sur l'API

L'erreur dans votre image indique que l'API n'est pas accessible.

**Solutions** :

1. **Vérifier que le backend est démarré** :
   ```bash
   # Testez dans un navigateur
   http://172.16.202.81:8000/api/v1
   ```

2. **Vérifier que le backend écoute sur toutes les interfaces** :
   - Utilisez `--host 0.0.0.0` (pas `localhost`)

3. **Vérifier le firewall** :
   - Autorisez le port 8000 dans Windows Firewall

4. **Tester la connexion** :
   ```powershell
   # Depuis votre appareil mobile, testez
   ping 172.16.202.81
   ```

## 🎯 Test Rapide de l'API

Testez que l'API fonctionne avant de lancer l'app :

```powershell
# Dans PowerShell
Invoke-WebRequest -Uri "http://172.16.202.81:8000/api/v1" -Method GET
```

Ou ouvrez dans un navigateur :
```
http://172.16.202.81:8000/api/v1
```

Vous devriez voir une réponse JSON (même si c'est une erreur 404, c'est normal).

## 📞 Besoin d'Aide ?

1. Vérifiez `LANCER_APP.md` pour le guide complet
2. Vérifiez `INSTALLATION_FLUTTER.md` pour installer Flutter
3. Vérifiez les logs du backend pour les erreurs


