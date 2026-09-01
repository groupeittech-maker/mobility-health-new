# Guide de dépannage - Frontend Simple

## Erreur "Failed to fetch"

Cette erreur se produit lorsque le navigateur ne peut pas se connecter au serveur backend.

### Causes possibles

1. **Serveur backend non démarré**
   - Le serveur FastAPI doit être en cours d'exécution sur `http://localhost:8000`
   - Vérifiez avec : `curl http://localhost:8000/health`

2. **Problème CORS**
   - Le backend doit autoriser les requêtes depuis votre origine
   - Vérifiez la configuration dans `app/core/config.py` : `CORS_ORIGINS`

3. **URL incorrecte**
   - Vérifiez que `API_BASE_URL` dans `js/api.js` correspond à votre configuration
   - Par défaut : `http://localhost:8000/api/v1`

4. **Fichiers servis via file://**
   - Les fichiers HTML ne doivent pas être ouverts directement (file://)
   - Utilisez un serveur HTTP local :
     ```bash
     # Python 3
     python -m http.server 8080
     
     # Node.js (avec http-server)
     npx http-server -p 8080
     ```

### Solutions

#### 1. Vérifier que le backend est démarré

```bash
# Dans le répertoire racine du projet
uvicorn app.main:app --reload

# Ou avec Docker
docker-compose up api
```

#### 2. Vérifier la configuration CORS

Dans `.env` ou `app/core/config.py`, assurez-vous que :
```python
CORS_ORIGINS = ["*", "http://localhost:8080", "http://127.0.0.1:8080"]
```

#### 3. Utiliser un serveur HTTP local

Ne pas ouvrir les fichiers HTML directement dans le navigateur. Utilisez un serveur :

```bash
# Option 1: Python
cd frontend-simple
python -m http.server 8080

# Option 2: Node.js
cd frontend-simple
npx http-server -p 8080

# Option 3: PHP
cd frontend-simple
php -S localhost:8080
```

Puis accédez à : `http://localhost:8080/admin-subscriptions.html`

#### 4. Utiliser le script de diagnostic

Le script `js/diagnostic.js` est inclus dans les pages. En mode développement, un bouton "🔍 Diagnostic" apparaît en bas à droite.

Cliquez dessus pour voir :
- Si le serveur backend répond
- Si les endpoints API sont accessibles
- Si CORS est configuré correctement
- Si un token est présent

#### 5. Vérifier la console du navigateur

Ouvrez les outils de développement (F12) et vérifiez :
- L'onglet **Console** pour les erreurs détaillées
- L'onglet **Network** pour voir les requêtes HTTP et leurs statuts

### Vérifications rapides

1. **Backend accessible ?**
   ```bash
   curl http://localhost:8000/health
   # Devrait retourner : {"status":"healthy"}
   ```

2. **API accessible ?**
   ```bash
   curl http://localhost:8000/api/v1/auth/me
   # Devrait retourner 401 (normal sans token)
   ```

3. **Token présent ?**
   - Ouvrez la console du navigateur (F12)
   - Tapez : `localStorage.getItem('access_token')`
   - Devrait retourner un token ou `null`

### Messages d'erreur courants

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Failed to fetch` | Backend non accessible | Démarrer le serveur backend |
| `CORS policy` | Problème CORS | Vérifier `CORS_ORIGINS` dans la config |
| `401 Unauthorized` | Token manquant/invalide | Se connecter à nouveau |
| `403 Forbidden` | Permissions insuffisantes | Vérifier le rôle utilisateur |
| `404 Not Found` | Endpoint inexistant | Vérifier l'URL de l'endpoint |

### Configuration recommandée

1. **Backend** : `http://localhost:8000`
2. **Frontend Simple** : `http://localhost:8080` (via serveur HTTP)
3. **CORS** : Autoriser `http://localhost:8080` dans la config backend

### Exemple de configuration complète

**Backend (.env)**
```
DATABASE_URL=postgresql://user:pass@localhost/mobilityhealth
CORS_ORIGINS=["*", "http://localhost:8080", "http://127.0.0.1:8080"]
```

**Frontend (js/api.js)**
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

**Démarrer le backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Démarrer le serveur frontend**
```bash
cd frontend-simple
python -m http.server 8080
```

**Accéder à l'application**
```
http://localhost:8080/admin-subscriptions.html
```


















