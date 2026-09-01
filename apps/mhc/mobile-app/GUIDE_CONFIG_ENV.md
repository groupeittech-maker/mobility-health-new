# 📝 Guide de Configuration du fichier .env

## 🎯 Configuration avec Backend Local + Production

Ce guide vous montre comment configurer votre fichier `.env` pour utiliser **à la fois** votre backend local et le backend de production.

---

## ✅ Configuration Recommandée

Voici la configuration complète pour votre fichier `.env` :

### 📋 Contenu complet du fichier `.env`

Créez ou modifiez le fichier `mobile-app/.env` avec ce contenu :

```env
# ============================================
# CONFIGURATION API
# ============================================

# URL principale : Backend Local (priorité 1)
# Utilisée en premier lorsque le backend local est démarré
API_BASE_URL=http://172.16.202.81:8000/api/v1

# URL secondaire : Backend de Production Hostinger (priorité 2)
# Utilisée automatiquement si le backend local n'est pas accessible
API_BASE_URL_SECONDARY=https://srv1324425.hstgr.cloud/api/v1

# ============================================
# CONFIGURATION GÉNÉRALE
# ============================================

# Timeout pour les requêtes API (en millisecondes)
API_TIMEOUT=30000

# Environnement : development ou production
ENVIRONMENT=development

# Nom de l'application
APP_NAME=Mobility Health

# Version de l'application
APP_VERSION=1.0.0
```

---

## 🔄 Comment ça fonctionne ?

L'application utilisera les URLs dans cet ordre :

1. **`API_BASE_URL`** → `http://172.16.202.81:8000/api/v1` (Backend Local)
   - Utilisée en premier
   - Parfaite pour le développement

2. **`API_BASE_URL_SECONDARY`** → `https://srv1324425.hstgr.cloud/api/v1` (Backend Production Hostinger)
   - Utilisée automatiquement si le local n'est pas accessible
   - Permet de continuer à travailler même si le backend local est arrêté

---

## 📂 Où placer le fichier `.env` ?

Le fichier `.env` doit être placé dans le dossier `mobile-app/` :

```
Mobility Health/
├── mobile-app/
│   ├── .env          ← ICI
│   ├── lib/
│   ├── pubspec.yaml
│   └── ...
```

---

## 🛠️ Comment créer/modifier le fichier `.env` ?

### Méthode 1 : Avec un éditeur de texte

1. Ouvrez votre éditeur de texte (VS Code, Notepad++, etc.)
2. Créez un nouveau fichier dans `mobile-app/`
3. Nommez-le exactement `.env` (avec le point au début)
4. Copiez-collez le contenu ci-dessus
5. Sauvegardez

### Méthode 2 : Avec PowerShell (Windows)

```powershell
# Aller dans le dossier mobile-app
cd "D:\logiciel et application\Mobility Health\mobile-app"

# Créer le fichier .env avec le contenu
@"
# URL principale : Backend Local
API_BASE_URL=http://172.16.202.81:8000/api/v1

# URL secondaire : Backend de Production Hostinger
API_BASE_URL_SECONDARY=https://srv1324425.hstgr.cloud/api/v1

# Configuration générale
API_TIMEOUT=30000
ENVIRONMENT=development
APP_NAME=Mobility Health
APP_VERSION=1.0.0
"@ | Out-File -FilePath ".env" -Encoding UTF8
```

### Méthode 3 : Vérifier si le fichier existe déjà

```powershell
# Vérifier si le fichier existe
Get-Content "mobile-app\.env"
```

---

## ✅ Vérification

Après avoir créé/modifié le fichier `.env`, vérifiez que tout est correct :

```powershell
# Afficher le contenu du fichier
Get-Content "mobile-app\.env"
```

Vous devriez voir toutes les lignes de configuration.

---

## 🔄 Après modification

**Important** : Après avoir modifié le fichier `.env`, vous devez :

1. **Arrêter l'application** si elle est en cours d'exécution (Ctrl+C)
2. **Redémarrer l'application** :
   ```powershell
   cd mobile-app
   flutter run
   ```

Les changements dans `.env` ne sont pris en compte qu'au démarrage de l'application.

---

## 🎯 Scénarios d'utilisation

### Scénario 1 : Backend Local démarré

- L'application se connecte à : `http://172.16.202.81:8000/api/v1`
- Vous pouvez développer et tester localement

### Scénario 2 : Backend Local arrêté

- L'application détecte que le local n'est pas accessible
- Elle bascule automatiquement vers : `https://srv1324425.hstgr.cloud/api/v1`
- Vous pouvez continuer à utiliser l'application avec les données de production

### Scénario 3 : Les deux backends disponibles

- L'application utilise toujours le local en priorité
- Le backend de production reste disponible en fallback

---

## 🔍 Vérifier quelle URL est utilisée

Lors du démarrage de l'application, les logs afficheront :

```
I/flutter: Initializing ApiClient with base URL: http://172.16.202.81:8000/api/v1
I/flutter: API Timeout: 30000ms
```

Cela vous permet de voir quelle URL est utilisée.

---

## ⚠️ Notes importantes

1. **Le fichier `.env` ne doit JAMAIS être commité dans Git**
   - Il est déjà dans `.gitignore`
   - Il contient des configurations spécifiques à votre environnement

2. **Les URLs sont normalisées automatiquement**
   - Vous pouvez omettre `/api/v1` à la fin, il sera ajouté automatiquement
   - Exemple : `http://172.16.202.81:8000` devient `http://172.16.202.81:8000/api/v1`

3. **Pour changer l'ordre de priorité**
   - Échangez simplement les valeurs de `API_BASE_URL` et `API_BASE_URL_SECONDARY`

---

## 🐛 Dépannage

### L'application n'utilise pas la bonne URL

1. Vérifiez que le fichier `.env` est bien dans `mobile-app/`
2. Vérifiez que le fichier contient les bonnes valeurs
3. **Redémarrez complètement l'application** (arrêtez avec Ctrl+C puis relancez)

### L'application ne se connecte pas

1. Vérifiez que le backend local est démarré :
   ```powershell
   # Testez dans un navigateur
   http://172.16.202.81:8000/api/v1
   ```

2. Vérifiez votre connexion réseau

3. Vérifiez que le port 8000 n'est pas bloqué par le firewall

---

## 📞 Besoin d'aide ?

Consultez aussi :
- `CONFIGURATION_BACKEND.md` pour plus de détails sur les configurations
- `LANCER_APP.md` pour le guide complet de lancement














