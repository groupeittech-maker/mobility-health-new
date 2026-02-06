# Résolution du problème : Endpoint /api/v1/subscriptions non disponible (404)

## 🔍 Diagnostic

L'endpoint `/api/v1/subscriptions` retourne une erreur 404, ce qui signifie que le serveur backend ne trouve pas cette route.

## ✅ Solutions

### Solution 1 : Redémarrer le serveur backend

Le problème le plus courant est que le serveur backend n'a pas rechargé les routes après des modifications.

**Étapes :**

1. Arrêter le serveur backend actuel (Ctrl+C dans le terminal où il tourne)

2. Redémarrer le serveur :
   ```powershell
   .\scripts\restart_backend.ps1
   ```

   Ou manuellement :
   ```powershell
   .\scripts\start_backend.ps1
   ```

3. Vérifier que le serveur démarre sans erreur

### Solution 2 : Vérifier les dépendances

Si le serveur ne démarre pas correctement, vérifier que toutes les dépendances sont installées :

```powershell
# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

### Solution 3 : Vérifier l'endpoint avec le script de diagnostic

Utiliser le script de diagnostic pour vérifier l'état de l'endpoint :

```powershell
.\scripts\check_subscriptions_endpoint.ps1
```

### Solution 4 : Vérifier les logs du serveur

Si le serveur démarre mais l'endpoint n'est toujours pas disponible, vérifier les logs du serveur pour des erreurs lors du chargement des routes.

## 🔧 Vérification manuelle

Pour vérifier manuellement que l'endpoint est disponible :

1. Ouvrir un navigateur ou utiliser curl :
   ```
   http://192.168.1.183:8000/api/v1/subscriptions
   ```

2. Vous devriez recevoir une erreur 401 (Unauthorized) si l'endpoint est disponible, ou 404 si l'endpoint n'existe pas.

3. Pour tester avec authentification, utiliser un outil comme Postman ou curl avec votre token :
   ```bash
   curl -H "Authorization: Bearer VOTRE_TOKEN" http://192.168.1.183:8000/api/v1/subscriptions
   ```

## 📋 Checklist

- [ ] Serveur backend redémarré
- [ ] Toutes les dépendances installées (`pip install -r requirements.txt`)
- [ ] Aucune erreur dans les logs du serveur
- [ ] Endpoint testé avec le script de diagnostic
- [ ] Application mobile relancée après redémarrage du serveur

## 🐛 Si le problème persiste

1. Vérifier que le fichier `app/api/v1/subscriptions.py` existe et contient la route `@router.get("/")`
2. Vérifier que le router est bien enregistré dans `app/api/v1/__init__.py` (ligne 76)
3. Vérifier les logs du serveur backend pour des erreurs d'import ou de syntaxe
4. Vérifier que le serveur écoute bien sur `http://192.168.1.183:8000`

## 📝 Notes

- L'endpoint `/api/v1/subscriptions` est défini dans `app/api/v1/subscriptions.py` ligne 179
- Le router est enregistré dans `app/api/v1/__init__.py` ligne 76
- L'endpoint nécessite une authentification (token Bearer)
