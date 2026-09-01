# Connexion de l'app mobile au backend en production

## Configuration utilisée

L'app est configurée pour le backend **https://srv1324425.hstgr.cloud**.

Le fichier **`.env`** à la racine de `mobile-app` contient :

```env
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud
API_TIMEOUT=30000
ENVIRONMENT=production
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

## Étapes pour lancer l'app et se connecter

### 1. Vérifier le fichier `.env`

Dans le dossier `mobile-app`, le fichier `.env` doit exister et contenir les lignes ci‑dessus.  
Si besoin, recréez‑le avec :

**Windows (PowerShell) :**
```powershell
cd "d:\logiciel et application\Mobility Health Nouveau\mobile-app"
.\create_env.ps1
```

**Linux / macOS :**
```bash
cd mobile-app
./create_env.sh
```

### 2. Récupérer les dépendances Flutter

```bash
cd mobile-app
flutter pub get
```

### 3. Lancer l'application

**Émulateur / appareil déjà sélectionné :**
```bash
flutter run
```

**Choisir un appareil :**
```bash
flutter devices
flutter run -d <device_id>
```

### 4. Se connecter dans l'app

- Ouvrir l’écran de connexion.
- Utiliser un compte existant sur le backend (ex. admin ou un utilisateur créé).
- Si l’app affiche une erreur réseau, vérifier que l’appareil/émulateur a bien accès à Internet.

## Vérifier que le backend répond

Dans un navigateur ou avec curl :

- **Racine API :** https://srv1324425.hstgr.cloud/api/v1  
- **Health :** https://srv1324425.hstgr.cloud/api/v1/health  

Vous devez voir du JSON (message de l’API ou `"status":"healthy"`).

## Dépannage

| Problème | Action |
|----------|--------|
| Timeout / pas de réponse | Vérifier la connexion Internet ; confirmer que l’URL dans `.env` est bien `https://srv1324425.hstgr.cloud/api/v1`. |
| Erreur de connexion | Vérifier que `.env` est à la racine de `mobile-app` et listé dans `pubspec.yaml` (assets). |
| 404 / Not Found | L’URL doit se terminer par `/api/v1` (sans slash final dans `.env`). |

Après toute modification de `.env`, relancer l’app (`flutter run`).
