# Configuration du Backend en Ligne

## URL du Backend de Production

L'application mobile est configurée pour se connecter au backend en ligne à l'adresse :

```
https://srv1324425.hstgr.cloud/api/v1
```

## Configuration dans le fichier `.env`

Pour utiliser le backend en ligne (Hostinger), assurez-vous que votre fichier `.env` contient :

```env
# Backend de production (Hostinger)
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud

# OU utilisez API_BASE_URL directement
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1

# Configuration générale
API_TIMEOUT=30000
ENVIRONMENT=production
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

## Ordre de Priorité des URLs

L'application utilise les URLs dans l'ordre suivant :

1. **API_BASE_URL** - URL principale (si définie)
2. **API_CONNEXION_BACKEND** - URL de connexion backend (si définie)
3. **API_BASE_URL_SECONDARY** - URL secondaire (si définie)
4. **API_BASE_URL_ADDITIONAL** - URLs supplémentaires (séparées par des virgules)
5. **Fallback** - `https://srv1324425.hstgr.cloud/api/v1` (backend Hostinger)

## Normalisation Automatique

L'application normalise automatiquement les URLs pour s'assurer qu'elles contiennent le préfixe `/api/v1`.

- Si vous spécifiez : `https://srv1324425.hstgr.cloud`
- L'application utilisera : `https://srv1324425.hstgr.cloud/api/v1`

## Vérification de la Connexion

Pour vérifier que la connexion fonctionne, vous pouvez :

1. Lancer l'application
2. Tenter de vous connecter
3. Vérifier les logs dans la console pour voir quelle URL est utilisée

## Configuration avec Backend Local ET Production (Recommandé)

Pour avoir les deux backends (local et production) avec fallback automatique :

### Option 1 : Local en priorité, Production en fallback

```env
# URL locale principale (priorité 1)
API_BASE_URL=http://172.16.202.81:8000/api/v1

# Backend de production en fallback (priorité 2)
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud

# OU utilisez l'URL secondaire
API_BASE_URL_SECONDARY=https://srv1324425.hstgr.cloud/api/v1

# Configuration générale
API_TIMEOUT=30000
ENVIRONMENT=development
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

L'application utilisera d'abord le backend local, puis basculera automatiquement vers la production si le local n'est pas accessible.

### Option 2 : Production en priorité, Local en fallback

```env
# Backend de production principale (priorité 1)
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1

# Backend local en fallback (priorité 2)
API_BASE_URL_SECONDARY=http://172.16.202.81:8000/api/v1

# Configuration générale
API_TIMEOUT=30000
ENVIRONMENT=production
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

L'application utilisera d'abord le backend de production, puis basculera automatiquement vers le local si la production n'est pas accessible.

## Configuration pour le Développement Local uniquement

Si vous voulez utiliser uniquement un backend local :

```env
API_BASE_URL=http://172.16.202.81:8000/api/v1
# ou
API_BASE_URL=http://localhost:8000/api/v1
ENVIRONMENT=development
```

## Notes Importantes

- L'URL du backend en ligne utilise HTTPS (sécurisé)
- Assurez-vous que votre certificat SSL est valide
- L'application gère automatiquement le fallback si une URL ne répond pas
- Les timeouts sont configurés à 30 secondes par défaut

