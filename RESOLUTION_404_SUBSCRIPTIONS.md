# 🔧 Résolution : Erreur 404 sur /api/v1/subscriptions

## 📋 Problème

L'application mobile affiche le message :
> "L'endpoint des souscriptions n'est pas disponible. Vérifiez que le serveur backend est démarré."

L'endpoint `/api/v1/subscriptions` retourne une erreur **404 Not Found**.

## ✅ Solution rapide (2 minutes)

### Étape 1 : Redémarrer le serveur backend

Ouvrez PowerShell dans le dossier du projet et exécutez :

```powershell
.\scripts\restart_backend.ps1
```

**OU** manuellement :

1. **Arrêter le serveur actuel** (si en cours d'exécution) :
   - Dans le terminal où le serveur tourne, appuyez sur `Ctrl+C`
   - Ou fermez le terminal

2. **Démarrer le serveur** :
   ```powershell
   .\scripts\start_backend.ps1
   ```

### Étape 2 : Vérifier que le serveur démarre correctement

Attendez que vous voyiez dans les logs :
```
Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**⚠️ Si vous voyez des erreurs d'import ou de syntaxe**, corrigez-les avant de continuer.

### Étape 3 : Tester l'endpoint

Exécutez le script de diagnostic :

```powershell
.\scripts\test_subscriptions_endpoint.ps1
```

Ce script va :
- ✅ Vérifier que le serveur backend est accessible
- ✅ Vérifier que l'endpoint est enregistré
- ✅ Tester l'endpoint `/api/v1/subscriptions`

### Étape 4 : Relancer l'application mobile

1. Fermez complètement l'application mobile
2. Relancez l'application
3. Connectez-vous avec votre compte
4. Allez dans "Mon historique" → "Souscriptions"

Les souscriptions devraient maintenant apparaître ! 🎉

## 🔍 Diagnostic approfondi

### Vérifier l'état des routes

Ouvrez dans votre navigateur :
```
http://192.168.1.183:8000/api/v1/
```

Vous devriez voir une réponse JSON avec :
- `routes_status.subscriptions_router_loaded: true`
- `routes_status.subscriptions_routes_count: [nombre]`

Si `subscriptions_router_loaded` est `false`, il y a une erreur lors du chargement du module.

### Vérifier la documentation Swagger

Ouvrez dans votre navigateur :
```
http://192.168.1.183:8000/docs
```

Cherchez l'endpoint `GET /api/v1/subscriptions`. S'il n'apparaît pas, le router n'est pas chargé.

### Vérifier les logs du serveur

Regardez les logs du serveur backend au démarrage. Vous devriez voir :
- Aucune erreur d'import
- Aucune erreur de syntaxe
- Les routes sont chargées

## 🐛 Si le problème persiste

### 1. Vérifier que le fichier existe

```powershell
Test-Path "app\api\v1\subscriptions.py"
```

Doit retourner `True`.

### 2. Vérifier la syntaxe Python

```powershell
python -m py_compile app\api\v1\subscriptions.py
```

Ne doit retourner aucune erreur.

### 3. Vérifier que le router est inclus

Ouvrez `app\api\v1\__init__.py` et vérifiez la ligne 87 :
```python
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
```

### 4. Tester l'import manuellement

```powershell
python -c "from app.api.v1 import subscriptions; print('OK')"
```

Ne doit retourner aucune erreur.

### 5. Vérifier les dépendances

```powershell
pip install -r requirements.txt
```

## 📝 Notes importantes

- **L'endpoint filtre par utilisateur** : Seules les souscriptions de l'utilisateur connecté sont retournées
- **Authentification requise** : L'endpoint nécessite un token valide
- **Redémarrage nécessaire** : Après toute modification du code backend, redémarrez le serveur

## 🎯 Checklist de résolution

- [ ] Serveur backend redémarré
- [ ] Aucune erreur dans les logs du serveur
- [ ] Script de diagnostic exécuté avec succès
- [ ] Endpoint visible dans Swagger (`/docs`)
- [ ] Application mobile relancée
- [ ] Souscriptions visibles dans l'historique

## 📞 Support

Si après avoir suivi toutes ces étapes le problème persiste :

1. Partagez les logs du serveur backend
2. Partagez le résultat du script `test_subscriptions_endpoint.ps1`
3. Vérifiez que vous êtes connecté avec le bon compte utilisateur
