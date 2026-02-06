# ✅ Bonnes Pratiques - URLs Presignées MinIO/AWS

## 📋 Principes Fondamentaux

### ❌ Ne JAMAIS stocker les URLs presignées en base de données

**Pourquoi ?**
- Les URLs presignées ont une durée de vie limitée (expiration)
- Stocker une URL expirée en base = erreur garantie
- Les URLs doivent être régénérées à chaque demande

### ✅ Toujours régénérer les URLs à la demande
**Comment ?**
- Utiliser uniquement le `chemin_fichier_minio` (la clé) stockée en base
- Régénérer l'URL presignée à chaque appel API
- Ne jamais utiliser `attestation.url_signee` comme source de vérité

## 🔧 Implémentation Actuelle

### Durées d'Expiration

**Avant :**
- URLs provisoires : 1 heure
- URLs dans les endpoints : 2 heures
- URLs définitives : 24 heures

**Après (amélioration) :**
- **Par défaut : 24 heures** (86400 secondes)
- Maximum recommandé : 7 jours (604800 secondes) pour AWS signature v4
- MinIO supporte aussi jusqu'à 7 jours

### Code Exemple

```python
from app.services.minio_service import MinioService
from datetime import timedelta

# ✅ BON : Régénérer à chaque demande
def get_attestation_url(attestation):
    # Utiliser uniquement le chemin stocké en base
    chemin = attestation.chemin_fichier_minio
    bucket = attestation.bucket_minio
    
    # Régénérer l'URL (24h d'expiration)
    url = MinioService.get_pdf_url(
        chemin_fichier=chemin,
        bucket_name=bucket,
        expires=timedelta(hours=24)
    )
    return url

# ❌ MAUVAIS : Utiliser l'URL stockée en base
def get_attestation_url_bad(attestation):
    return attestation.url_signee  # ❌ Peut être expirée !
```

## 📝 Modifications Apportées

### 1. Durées d'Expiration Augmentées

**Fichier :** `app/services/minio_service.py`

```python
# Avant
expires: timedelta = timedelta(hours=1)  # ❌ Trop court

# Après
expires: timedelta = timedelta(hours=24)  # ✅ 24h par défaut
```

### 2. Régénération Systématique

**Fichiers modifiés :**
- `app/api/v1/attestations.py`
- `app/api/v1/documents.py`
- `app/services/attestation_service.py`

**Changements :**
- Tous les endpoints régénèrent maintenant les URLs à chaque demande
- Les URLs stockées en base sont ignorées (utilisées uniquement pour compatibilité)
- Commentaires ajoutés : "NE JAMAIS utiliser les URLs stockées en base"

### 3. Gestion des Erreurs d'Expiration

Le système détecte automatiquement les URLs expirées et les régénère :
- Détection via `MinioService.is_expired_url_error()`
- Régénération automatique
- Logging détaillé pour le diagnostic

## 🎯 Endpoints Modifiés

### `/subscriptions/{subscription_id}/attestations`
- Régénère les URLs à chaque demande
- Durée : 24 heures

### `/users/me/attestations`
- Régénère les URLs à chaque demande
- Durée : 24 heures

### `/attestations/{attestation_id}`
- Régénère l'URL à chaque demande
- Durée : 24 heures

### `/documents`
- Régénère les URLs à chaque demande
- Durée : 24 heures

## 🔍 Vérification

Pour vérifier qu'une URL est toujours régénérée :

```python
# Dans un endpoint
attestation = db.query(Attestation).filter(...).first()

# ✅ Toujours régénérer
url = MinioService.get_pdf_url(
    attestation.chemin_fichier_minio,
    attestation.bucket_minio,
    timedelta(hours=24)
)

# ❌ Ne jamais faire ça
url = attestation.url_signee  # Peut être expirée !
```

## 📊 Comparaison Avant/Après

| Aspect | Avant | Après |
|--------|-------|-------|
| Durée expiration | 1-2 heures | 24 heures |
| Stockage en base | ✅ Oui (problématique) | ⚠️ Oui (ignoré) |
| Régénération | Parfois | ✅ Toujours |
| Gestion expiration | Manuelle | ✅ Automatique |

## 🚀 Recommandations Futures

### Option 1 : Supprimer les champs de la base (Migration)

```python
# Migration Alembic
def upgrade():
    # Supprimer les colonnes url_signee et date_expiration_url
    op.drop_column('attestations', 'url_signee')
    op.drop_column('attestations', 'date_expiration_url')
    op.drop_column('attestations', 'carte_numerique_url')
    op.drop_column('attestations', 'carte_numerique_expires_at')
```

### Option 2 : Garder pour compatibilité (Recommandé)

- Garder les champs en base pour compatibilité
- Ne jamais les utiliser comme source de vérité
- Toujours régénérer à partir de `chemin_fichier_minio`

## 📚 Références

- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
- [MinIO Presigned URLs](https://min.io/docs/minio/linux/developers/python/API.html#presigned_get_object)
- [GESTION_ERREURS_MINIO.md](./GESTION_ERREURS_MINIO.md) : Gestion des erreurs

## ✅ Checklist de Vérification

- [x] Durées d'expiration augmentées (24h)
- [x] Régénération systématique dans tous les endpoints
- [x] Commentaires ajoutés pour éviter l'utilisation des URLs stockées
- [x] Gestion automatique des erreurs d'expiration
- [x] Logging amélioré
- [ ] Migration pour supprimer les champs (optionnel, futur)

## 🎓 Résumé

**Règle d'or :** 
> Ne jamais stocker les URLs presignées en base. Toujours les régénérer à partir de la clé (chemin du fichier) stockée en base.

**Durée recommandée :**
- 24 heures pour un usage normal
- 7 jours maximum (604800 secondes) si nécessaire

**Gestion des erreurs :**
- Détection automatique des URLs expirées
- Régénération automatique
- Messages d'erreur clairs

