# 🚀 Guide de démarrage rapide - Mobility Health

## ⚠️ IMPORTANT : Le frontend DOIT être servi via HTTP

**Ne jamais ouvrir les fichiers HTML directement** (double-clic) car cela utilise `file://` et bloque les requêtes CORS.

## 📋 Étapes de démarrage

### 1️⃣ Démarrer le Backend

Ouvrez un terminal PowerShell dans la **racine du projet** :

```powershell
# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Démarrer le serveur backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**OU** utilisez le script :

```powershell
.\scripts\start_backend.ps1
```

Vous devriez voir :
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 2️⃣ Démarrer le Frontend

Ouvrez un **NOUVEAU** terminal PowerShell :

```powershell
# Aller dans le dossier frontend
cd frontend-simple

# Démarrer le serveur HTTP
python server.py
```

**OU** utilisez le script depuis la racine :

```powershell
.\scripts\start_frontend.ps1
```

Le serveur démarre sur `http://localhost:3000`

### 3️⃣ Accéder à l'application

Ouvrez votre navigateur et allez sur :
- **Page de connexion** : http://localhost:3000/login.html
- **Page d'accueil** : http://localhost:3000/index.html

## ✅ Vérifications

### Vérifier que le backend fonctionne

```powershell
# Test 1: Health check
curl http://localhost:8000/health
# Devrait retourner: {"status":"healthy"}

# Test 2: Endpoint de login
curl -X POST http://localhost:8000/api/v1/auth/login -d "username=test&password=test"
# Devrait retourner 401 (normal pour identifiants incorrects)
```

### Vérifier que le frontend est bien servi

Dans la barre d'adresse du navigateur, vous devez voir :
- ✅ `http://localhost:3000/login.html` (CORRECT)
- ❌ `file:///D:/.../login.html` (INCORRECT - ne fonctionnera pas)

## 🐛 Problèmes courants

### "Failed to fetch" dans la console

**Cause** : Le frontend n'est pas servi via HTTP ou le backend n'est pas démarré.

**Solution** :
1. Vérifiez que le backend est démarré (voir étape 1)
2. Vérifiez que le frontend est servi via HTTP (voir étape 2)
3. Vérifiez l'URL dans la barre d'adresse du navigateur

### Erreur CORS dans la console

**Cause** : Le backend n'autorise pas l'origine du frontend.

**Solution** : Vérifiez que `http://localhost:3000` est dans `CORS_ORIGINS` dans `.env` ou `app/core/config.py`

### Le backend ne démarre pas

**Causes possibles** :
- Port 8000 déjà utilisé
- Base de données non accessible
- Redis non accessible (utilise fakeredis en développement)

**Solution** :
```powershell
# Arrêter les processus sur le port 8000
netstat -ano | findstr :8000
# Notez le PID et arrêtez-le avec:
taskkill /F /PID <PID>

# Redémarrer le backend
.\scripts\start_backend.ps1
```

## 📝 Commandes utiles

```powershell
# Arrêter tous les processus Python
Get-Process python | Stop-Process -Force

# Vérifier les ports utilisés
netstat -ano | findstr ":8000\|:3000"

# Tester la connexion au backend
python scripts/test_login_quick.py
```

## 🔧 Configuration

### Backend (.env)
```env
DATABASE_URL=postgresql://user:pass@localhost/mobilityhealth
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

### Frontend (frontend-simple/js/api.js)
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

## 📞 Aide supplémentaire

Si le problème persiste :
1. Ouvrez la console du navigateur (F12)
2. Regardez l'onglet **Network** pour voir les requêtes HTTP
3. Vérifiez les erreurs dans l'onglet **Console**
4. Exécutez le script de diagnostic : `python scripts/test_login_quick.py`

