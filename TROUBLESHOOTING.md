# Guide de Dépannage - Mobility Health

## Erreur : "Impossible de se connecter au serveur" / "Failed to fetch"

### Symptômes
- Erreur dans la console : `Failed to fetch`
- Message : "Impossible de se connecter au serveur backend sur http://localhost:8000"
- La page frontend ne peut pas charger les données depuis l'API

### Causes possibles

1. **Le backend n'est pas démarré**
   - Le serveur FastAPI n'est pas en cours d'exécution
   - Le port 8000 n'est pas accessible

2. **Le backend est démarré sur un autre port**
   - Vérifiez le port dans les logs du serveur
   - Modifiez `API_BASE_URL` dans `frontend-simple/js/api.js` si nécessaire

3. **Problème de CORS**
   - Le backend bloque les requêtes depuis le frontend
   - Vérifiez la configuration CORS dans `app/core/config.py`

4. **Services dépendants non démarrés**
   - PostgreSQL, Redis ou Minio ne sont pas démarrés
   - Le backend ne peut pas se connecter à la base de données

### Solutions

#### 1. Démarrer le backend

**Option A : Avec Docker Compose (recommandé)**
```bash
# Démarrer tous les services (backend + base de données + Redis + Minio)
docker-compose up -d

# Vérifier que le backend est démarré
docker-compose ps

# Voir les logs
docker-compose logs -f api
```

**Option B : Démarrage local (sans Docker)**
```bash
# Windows PowerShell
.\scripts\start_backend.ps1

# Linux/Mac
chmod +x scripts/start_backend.sh
./scripts/start_backend.sh

# Ou manuellement
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Vérifier que le backend fonctionne

Ouvrez dans votre navigateur :
- **API Health Check** : http://localhost:8000/health
- **Documentation API** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

Si ces pages ne s'ouvrent pas, le backend n'est pas démarré.

#### 3. Vérifier les services dépendants

**Avec Docker Compose :**
```bash
# Vérifier l'état de tous les services
docker-compose ps

# Démarrer uniquement les services de base (sans le backend)
docker-compose up -d db redis minio
```

**Sans Docker :**
- PostgreSQL doit être accessible sur `localhost:5432`
- Redis doit être accessible sur `localhost:6379`
- Minio doit être accessible sur `localhost:9000`

#### 4. Vérifier la configuration

**Fichier `.env` :**
```bash
# Vérifiez que le fichier .env existe
# S'il n'existe pas, copiez env.example
cp env.example .env

# Vérifiez les variables importantes :
# - DATABASE_URL
# - REDIS_URL
# - MINIO_ENDPOINT
# - SECRET_KEY
```

**Configuration CORS :**
Le fichier `app/core/config.py` doit contenir :
```python
CORS_ORIGINS: List[str] = ["*", "http://localhost:3000", "http://127.0.0.1:3000"]
```

#### 5. Vérifier les logs

**Avec Docker :**
```bash
# Logs du backend
docker-compose logs -f api

# Logs de tous les services
docker-compose logs -f
```

**Sans Docker :**
Les logs s'affichent directement dans le terminal où vous avez démarré le serveur.

### Vérification rapide

1. **Test de connexion au backend :**
   ```bash
   curl http://localhost:8000/health
   ```
   Devrait retourner : `{"status":"healthy"}`

2. **Test de l'endpoint API :**
   ```bash
   curl http://localhost:8000/api/v1/products
   ```
   Devrait retourner une liste de produits (ou une erreur d'authentification si non connecté)

3. **Vérifier le port :**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

### Problèmes courants

#### Le port 8000 est déjà utilisé
```bash
# Trouver le processus qui utilise le port
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# Tuer le processus (remplacez PID par le numéro du processus)
# Windows
taskkill /PID <PID> /F

# Linux/Mac
kill -9 <PID>
```

#### Erreur de connexion à la base de données
```bash
# Vérifier que PostgreSQL est démarré
# Avec Docker
docker-compose ps db

# Tester la connexion
psql -h localhost -U postgres -d mobility_health
```

#### Erreur CORS
Si vous voyez des erreurs CORS dans la console :
1. Vérifiez que `CORS_ORIGINS` dans `.env` inclut l'origine de votre frontend
2. Redémarrez le backend après modification de la configuration

### Support

Si le problème persiste :
1. Vérifiez les logs du backend pour plus de détails
2. Vérifiez que tous les services sont démarrés
3. Vérifiez la configuration dans `.env`
4. Consultez la documentation API sur http://localhost:8000/docs

