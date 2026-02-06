# Guide de démarrage du serveur API

## Problème de connexion admin/admin123

Si vous ne pouvez pas vous connecter avec `admin/admin123`, vérifiez que le serveur API est démarré.

## Démarrage du serveur API

### Option 1 : Avec uvicorn (recommandé)

```bash
# Activer l'environnement virtuel
.\venv\Scripts\activate

# Démarrer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2 : Avec Python directement

```bash
# Activer l'environnement virtuel
.\venv\Scripts\activate

# Démarrer le serveur
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Vérification

Une fois le serveur démarré, vous devriez voir :
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Test de connexion

1. Ouvrez votre navigateur sur `http://localhost:8080/login.html` (ou le port configuré)
2. Utilisez les identifiants :
   - **Username:** `admin`
   - **Password:** `admin123`

## Vérifier que le compte admin existe

Si le problème persiste, exécutez :

```bash
python scripts/check_admin_user.py
```

## Réinitialiser le mot de passe admin

Si nécessaire :

```bash
python scripts/reset_admin_password.py
```

## Créer tous les utilisateurs de test

Pour créer/réinitialiser tous les comptes de test :

```bash
python scripts/create_test_users.py
```

## Dépannage

### Le serveur ne démarre pas

1. Vérifiez que la base de données est accessible
2. Vérifiez les variables d'environnement dans `.env`
3. Vérifiez les logs d'erreur

### Erreur de connexion à la base de données

Assurez-vous que PostgreSQL est démarré et que la base de données existe :

```bash
# Créer la base de données si nécessaire
psql -U postgres -c "CREATE DATABASE mobility_health;"

# Exécuter les migrations
alembic upgrade head
```

### Erreur "Connection refused"

- Vérifiez que le serveur est bien démarré sur le port 8000
- Vérifiez le firewall
- Vérifiez l'URL dans `frontend-simple/js/api.js` (par défaut: `http://localhost:8000/api/v1`)

