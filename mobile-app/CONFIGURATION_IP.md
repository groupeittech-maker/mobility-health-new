# 📡 Configuration des Adresses IP pour le Backend

## 🔧 Ajouter une Nouvelle Adresse IP

Pour ajouter une nouvelle adresse IP sans supprimer l'existante, vous avez plusieurs options :

### Option 1 : URL Secondaire (Recommandé)

Ajoutez dans votre fichier `.env` :

```env
# URL principale (existante)
API_BASE_URL=http://172.16.202.81:8000/api/v1

# URL secondaire (nouvelle)
API_BASE_URL_SECONDARY=http://172.16.202.81:8000/api/v1
```

L'application utilisera d'abord `API_BASE_URL`, et pourra basculer vers `API_BASE_URL_SECONDARY` si nécessaire.

### Option 2 : URLs Additionnelles

Pour ajouter plusieurs URLs supplémentaires :

```env
# URL principale
API_BASE_URL=http://172.16.202.81:8000/api/v1

# URLs additionnelles (séparées par des virgules)
API_BASE_URL_ADDITIONAL=http://172.16.202.81:8000/api/v1,http://10.0.0.1:8000/api/v1
```

### Option 3 : Changer l'URL Principale

Si vous voulez utiliser la nouvelle adresse comme principale :

```env
# Ancienne adresse en secondaire
API_BASE_URL_SECONDARY=http://172.16.202.81:8000/api/v1

# Nouvelle adresse principale
API_BASE_URL=http://172.16.202.81:8000/api/v1
```

## 📝 Exemple de Configuration Complète

```env
# Configuration actuelle avec les deux adresses
API_BASE_URL=http://172.16.202.81:8000/api/v1
API_BASE_URL_SECONDARY=http://172.16.202.81:8000/api/v1

# Autres configurations
API_TIMEOUT=30000
ENVIRONMENT=development
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

## 🔄 Comment ça Fonctionne

1. L'application lit d'abord `API_BASE_URL` (URL principale)
2. Si `API_BASE_URL_SECONDARY` est défini, il est ajouté à la liste de fallback
3. Si `API_BASE_URL_ADDITIONAL` est défini, toutes les URLs sont ajoutées
4. L'application utilise toujours la première URL de la liste par défaut

## ✅ Vérification

Après modification du fichier `.env`, redémarrez l'application :

```powershell
# Arrêter l'application (Ctrl+C)
# Puis relancer
flutter run
```

## 🧪 Tester la Connexion

Pour tester si les deux adresses sont accessibles :

```powershell
# Tester l'ancienne adresse
Invoke-WebRequest -Uri "http://172.16.202.81:8000/api/v1" -Method GET

# Tester la nouvelle adresse
Invoke-WebRequest -Uri "http://172.16.202.81:8000/api/v1" -Method GET
```

Les deux devraient retourner un JSON avec les informations de l'API.

