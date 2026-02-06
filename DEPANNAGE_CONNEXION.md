# 🔧 Dépannage - Problème de connexion user/user123

## ✅ Vérifications effectuées

Le backend fonctionne correctement :
- ✓ L'utilisateur 'user' existe dans la base de données
- ✓ Le mot de passe 'user123' est correct
- ✓ L'endpoint de login fonctionne
- ✓ Le token est généré correctement

## 🔍 Causes possibles côté frontend

### 1. Fichiers ouverts directement (file://)

**Problème** : Si vous ouvrez les fichiers HTML directement dans le navigateur (double-clic), les requêtes CORS échoueront.

**Solution** : Utilisez un serveur HTTP local :

```bash
# Option 1: Python
cd frontend-simple
python -m http.server 3000

# Option 2: Node.js (si installé)
cd frontend-simple
npx http-server -p 3000

# Option 3: PHP (si installé)
cd frontend-simple
php -S localhost:3000
```

Puis accédez à : `http://localhost:3000/login.html`

### 2. Backend non démarré

**Vérification** :
```bash
# Tester si le backend répond
curl http://localhost:8000/health
```

**Solution** : Démarrer le backend :
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Problème CORS

**Vérification** : Ouvrez la console du navigateur (F12) et regardez les erreurs.

**Solution** : Vérifier la configuration CORS dans `app/core/config.py` :
```python
CORS_ORIGINS = ["*", "http://localhost:3000", "http://127.0.0.1:3000"]
```

### 4. URL de l'API incorrecte

**Vérification** : Ouvrez la console du navigateur (F12) et vérifiez l'URL utilisée.

**Solution** : Vérifier `frontend-simple/js/api.js` ou définir `window.API_BASE_URL` :
```javascript
window.API_BASE_URL = 'http://localhost:8000/api/v1';
```

## 🧪 Tests à effectuer

### Test 1: Vérifier le backend
```bash
python scripts/test_login.py
```

### Test 2: Vérifier l'utilisateur
```bash
python scripts/fix_user_login.py
```

### Test 3: Tester depuis le navigateur

1. Ouvrez `http://localhost:3000/login.html` (via serveur HTTP)
2. Ouvrez la console (F12)
3. Essayez de vous connecter avec `user` / `user123`
4. Regardez les erreurs dans la console

## 📋 Checklist de dépannage

- [ ] Backend démarré sur http://localhost:8000
- [ ] Frontend servi via HTTP (pas file://)
- [ ] URL correcte : http://localhost:3000/login.html
- [ ] Console du navigateur ouverte (F12)
- [ ] Pas d'erreurs CORS dans la console
- [ ] Utilisateur 'user' existe (vérifié avec `fix_user_login.py`)

## 🐛 Erreurs courantes

### "Failed to fetch"
- **Cause** : Backend non accessible ou problème CORS
- **Solution** : Vérifier que le backend est démarré et que CORS est configuré

### "Incorrect username or password"
- **Cause** : Utilisateur inexistant ou mot de passe incorrect
- **Solution** : Exécuter `python scripts/fix_user_login.py`

### "User is inactive"
- **Cause** : Compte utilisateur désactivé
- **Solution** : Exécuter `python scripts/fix_user_login.py` pour réactiver

### Erreur CORS dans la console
- **Cause** : Configuration CORS incorrecte
- **Solution** : Vérifier `CORS_ORIGINS` dans la configuration backend

## 📞 Commandes utiles

```bash
# Vérifier l'utilisateur
python scripts/fix_user_login.py

# Tester la connexion
python scripts/test_login.py

# Créer tous les utilisateurs de test
python scripts/create_test_users.py

# Vérifier un utilisateur spécifique
python scripts/check_user.py user
```

## ✅ Solution rapide

Si rien ne fonctionne, essayez cette séquence :

1. **Démarrer le backend** :
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Dans un autre terminal, démarrer le serveur frontend** :
   ```bash
   cd frontend-simple
   python -m http.server 3000
   ```

3. **Vérifier/créer l'utilisateur** :
   ```bash
   python scripts/fix_user_login.py
   ```

4. **Ouvrir dans le navigateur** :
   ```
   http://localhost:3000/login.html
   ```

5. **Se connecter avec** :
   - Username: `user`
   - Password: `user123`

## 📝 Notes

- L'utilisateur 'user' existe et fonctionne (vérifié avec les scripts)
- Le backend répond correctement aux requêtes de login
- Le problème est probablement lié à la configuration frontend ou au serveur HTTP

