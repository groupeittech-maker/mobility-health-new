# 🔧 Gestion des Erreurs MinIO - Mobility Health

## 📋 Problèmes Identifiés

### 1. Erreur `AccessDenied: Request has expired`

Cette erreur se produit lorsque :
- Une URL signée MinIO a expiré
- L'heure du serveur est incorrecte (en avance ou en retard)
- La synchronisation NTP n'est pas correctement configurée

**Format de l'erreur :**
```xml
<Error>
  <Code>AccessDenied</Code>
  <Message>Request has expired</Message>
  <Key>42/provisoire/ATT-PROV-SUB-ACB032AB-20251202-20251202-A1C2A49A_71a9bf8a.pdf</Key>
  <BucketName>attestations</BucketName>
  <Resource>/attestations/42/provisoire/...</Resource>
</Error>
```

### 2. Erreur `NoSuchKey`

Cette erreur se produit lorsque :
- Le fichier n'existe pas dans MinIO
- Le chemin du fichier est incorrect
- Le fichier a été supprimé

### 3. Erreur XML Incomplète

Cette erreur se produit lorsque :
- L'erreur MinIO est mal formatée ou incomplète
- Seulement `<Resource>`, `<RequestId>`, et `<HostId>` sont présents
- Le `<Code>` et `<Message>` sont absents

**Format de l'erreur :**
```xml
<Erreur>
  <Resource>/attestations/41/provisoire/ATT-PROV-SUB-8129A353-20251202-20251202-8F058252_f77f671b.pdf</Resource>
  <RequestId>187DC6F697384E52</RequestId>
  <HostId>dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8</HostId>
</Erreur>
```

## ✅ Améliorations Apportées

### 1. Extraction Complète des Détails d'Erreur

**Fichier :** `app/services/minio_service.py`

- Ajout de la méthode `extract_error_details()` pour extraire toutes les informations disponibles
- Extraction depuis les attributs de l'exception ET depuis le XML si présent
- Capture de : `code`, `message`, `resource`, `request_id`, `host_id`, `bucket_name`, `key`
- Gestion des erreurs XML incomplètes ou mal formatées

### 2. Détection Automatique des URLs Expirées

**Fichier :** `app/services/minio_service.py`

- Ajout de la méthode `is_expired_url_error()` pour détecter les erreurs d'expiration
- Utilise `extract_error_details()` pour une analyse plus complète
- Régénération automatique des URLs expirées dans `generate_signed_url()`
- Logging détaillé pour le diagnostic

**Exemple d'utilisation :**
```python
# Extraire tous les détails d'une erreur
error_details = MinioService.extract_error_details(error)
print(f"Code: {error_details['code']}")
print(f"Message: {error_details['message']}")
print(f"Resource: {error_details['resource']}")
print(f"RequestId: {error_details['request_id']}")

# Détecter si c'est une URL expirée
if MinioService.is_expired_url_error(error):
    # L'URL a expiré, régénération automatique
    url = MinioService.get_pdf_url(chemin_fichier, bucket_name, expires)
```

### 3. Vérification d'Existence des Fichiers

**Fichier :** `app/services/minio_service.py`

- Ajout de la méthode `file_exists()` pour vérifier l'existence avant l'accès
- Vérification automatique avant la génération d'URLs signées
- Messages d'erreur plus clairs

### 4. Gestion d'Erreurs Améliorée dans les Endpoints

**Fichiers modifiés :**
- `app/api/v1/documents.py`
- `app/api/v1/attestations.py`
- `app/api/v1/subscriptions.py`

**Améliorations :**
- Détection spécifique des erreurs d'expiration
- Régénération automatique des URLs expirées
- Fallback vers téléchargement direct en cas d'échec
- Messages d'erreur plus informatifs avec codes d'erreur MinIO

### 5. Logging Détaillé

Tous les endpoints loggent maintenant :
- Le code d'erreur MinIO (`AccessDenied`, `NoSuchKey`, etc.)
- Le message d'erreur complet
- Le Resource (chemin complet)
- Le RequestId (pour le suivi)
- Le HostId (si disponible)
- Le chemin du fichier concerné
- L'ID de l'attestation
- Les tentatives de régénération

## 🔍 Diagnostic

### Vérifier si un fichier existe

```python
from app.services.minio_service import MinioService

exists = MinioService.file_exists(
    "attestations",
    "42/provisoire/ATT-PROV-SUB-ACB032AB-20251202-20251202-A1C2A49A_71a9bf8a.pdf"
)
```

### Vérifier la synchronisation de l'heure

Consultez le fichier `NTP_SYNCHRONISATION.md` pour :
- Vérifier l'heure du serveur
- Configurer la synchronisation NTP
- Corriger les problèmes d'heure

### Logs à surveiller

Recherchez dans les logs :
- `URL expirée détectée` : Indique qu'une URL a expiré
- `URL régénérée avec succès` : La régénération a réussi
- `Échec de la régénération` : Problème de synchronisation d'heure probable
- `Erreur MinIO [AccessDenied]` : Erreur d'accès avec détails

## 🚀 Comportement Automatique

### Régénération Automatique

Lorsqu'une URL expirée est détectée :
1. Le système détecte automatiquement l'erreur
2. Tente de régénérer l'URL immédiatement
3. Si la régénération réussit, l'URL est mise à jour
4. Si la régénération échoue, un message d'erreur clair est retourné

### Fallback Intelligent

En cas d'erreur lors du téléchargement direct :
1. Le système tente d'abord le téléchargement direct depuis MinIO
2. Si cela échoue, fallback vers une URL signée régénérée
3. Si la régénération échoue, message d'erreur avec instructions

## 📝 Messages d'Erreur Améliorés

### Avant
```
Erreur lors de la génération de l'URL
```

### Après
```
Erreur MinIO [AccessDenied] lors de la génération de l'URL signée pour 
attestations/42/provisoire/ATT-PROV-SUB-ACB032AB-20251202-20251202-A1C2A49A_71a9bf8a.pdf: 
Request has expired. URL régénérée avec succès.
```

## ⚠️ Actions Recommandées

1. **Vérifier la synchronisation NTP** : Consultez `NTP_SYNCHRONISATION.md`
2. **Surveiller les logs** : Recherchez les erreurs `AccessDenied` et `Request has expired`
3. **Vérifier l'existence des fichiers** : Utilisez `MinioService.file_exists()` pour diagnostiquer
4. **Redémarrer le serveur** : Après correction de l'heure, redémarrer le serveur backend

## 🔗 Fichiers Modifiés

- `app/services/minio_service.py` : Détection et régénération automatique
- `app/api/v1/documents.py` : Gestion d'erreurs améliorée
- `app/api/v1/attestations.py` : Gestion d'erreurs améliorée
- `app/api/v1/subscriptions.py` : Gestion d'erreurs améliorée

## 📚 Documentation Associée

- `NTP_SYNCHRONISATION.md` : Guide de synchronisation de l'heure
- `TROUBLESHOOTING.md` : Guide général de dépannage

