# ✅ Vérification : Base de Données Unique

## 🎯 Confirmation

**TOUS LES CLIENTS (Mobile, Frontend Web, Backoffice) UTILISENT LA MÊME BASE DE DONNÉES UNIQUE**

---

## 📊 Architecture

```
┌─────────────────┐
│  PostgreSQL 15  │
│  mobility_health │
│  localhost:5432  │
└────────┬─────────┘
         │
         │ DATABASE_URL
         │
┌────────▼─────────┐
│  Backend FastAPI │
│  :8000/api/v1    │
└────────┬─────────┘
         │
    ┌────┴────┬──────────────┬──────────────┐
    │         │              │              │
    │         │              │              │
┌───▼───┐ ┌──▼──────┐  ┌─────▼─────┐  ┌────▼──────┐
│Mobile │ │Frontend │  │ Backoffice │  │  Autres   │
│  App  │ │   Web   │  │  (Admin)   │  │  Clients  │
└───────┘ └─────────┘  └────────────┘  └───────────┘
```

---

## 🔹 Base de Données Unique

- **Nom** : `mobility_health`
- **Type** : PostgreSQL 15
- **Host** : `localhost:5432` (ou `db:5432` dans Docker)
- **User** : `postgres`
- **Password** : `postgres` (configurable via `.env`)

### Configuration Backend

**Fichier** : `.env` (racine du projet)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mobility_health
```

**Fichier** : `docker-compose.yml`
```yaml
services:
  db:
    POSTGRES_DB: mobility_health
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  
  api:
    DATABASE_URL: postgresql://postgres:postgres@db:5432/mobility_health
```

---

## 🔹 Backend (FastAPI)

- **URL API** : `http://localhost:8000/api/v1`
- **DATABASE_URL** : `postgresql://postgres:postgres@localhost:5432/mobility_health`
- **✅ Connecté à la base de données unique**

**Fichier de configuration** : `app/core/config.py`
```python
class Settings(BaseSettings):
    DATABASE_URL: str  # Chargé depuis .env
```

**Fichier de connexion** : `app/core/database.py`
```python
engine = create_engine(settings.DATABASE_URL, ...)
```

---

## 🔹 Mobile App

- **API_BASE_URL** : `http://192.168.1.183:8000/api/v1` (local)
- **API_BASE_URL_SECONDARY** : `http://10.0.2.2:8000/api/v1` (émulateur Android)
- **✅ Pointe vers le même backend → même base de données**

**Fichier** : `mobile-app/.env`
```env
API_BASE_URL=http://192.168.1.183:8000/api/v1
API_BASE_URL_SECONDARY=http://10.0.2.2:8000/api/v1
```

**Fichier** : `mobile-app/lib/core/config/app_config.dart`
```dart
static List<String> get apiBaseUrls {
  final primaryUrl = dotenv.env['API_BASE_URL'];
  // ...
}
```

---

## 🔹 Frontend Web

- **API_BASE_URL** : `http://localhost:8000/api/v1`
- **✅ Pointe vers le même backend → même base de données**

**Fichier** : `frontend-simple/js/api.js`
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
window.API_BASE_URL = API_BASE_URL;
```

---

## 🔹 Backoffice

- **Intégré dans** : `frontend-simple` (pages `admin-*.html`)
- **Utilise la même** : `API_BASE_URL` que le frontend web
- **✅ Pointe vers le même backend → même base de données**

**Pages Backoffice** :
- `admin-dashboard.html` - Tableau de bord administrateur
- `admin-subscriptions.html` - Gestion des souscriptions
- `admin-users.html` - Gestion des utilisateurs
- `admin-products.html` - Gestion des produits
- `admin-attestations.html` - Validation des attestations
- `doctor-dashboard.html` - Tableau de bord médecin
- `hospital-dashboard.html` - Tableau de bord hôpital
- `finance-dashboard.html` - Tableau de bord finance
- `sos-dashboard.html` - Tableau de bord SOS

**Toutes ces pages utilisent** : `frontend-simple/js/api.js` qui pointe vers `http://localhost:8000/api/v1`

---

## ✅ Conclusion

### Architecture Centralisée

1. **Une seule base de données PostgreSQL** : `mobility_health`
2. **Un seul backend FastAPI** : `http://localhost:8000/api/v1`
3. **Tous les clients se connectent au même backend** :
   - ✅ Mobile App → Backend → Base de données
   - ✅ Frontend Web → Backend → Base de données
   - ✅ Backoffice → Backend → Base de données

### Avantages

- ✅ **Cohérence des données** : Tous les clients voient les mêmes données
- ✅ **Synchronisation automatique** : Les modifications sont immédiatement visibles partout
- ✅ **Gestion centralisée** : Un seul point d'accès à la base de données
- ✅ **Sécurité** : Un seul point de contrôle d'accès
- ✅ **Maintenance simplifiée** : Une seule base de données à maintenir

### Vérification

Pour vérifier que tous utilisent la même base :

1. **Créer un utilisateur via le mobile** → Vérifier qu'il apparaît dans le backoffice
2. **Créer une souscription via le frontend web** → Vérifier qu'elle apparaît dans le mobile
3. **Valider une attestation dans le backoffice** → Vérifier qu'elle apparaît dans le mobile et le frontend

---

## 📝 Notes

- Le backend FastAPI est le **point d'entrée unique** pour tous les clients
- La base de données PostgreSQL est **partagée** entre tous les clients
- Les différences d'URL (`localhost:8000` vs `192.168.1.183:8000`) sont uniquement dues aux **configurations réseau** (même serveur, adresses différentes selon le contexte)
- Le backoffice est **intégré** dans le frontend web, pas une application séparée

---

**Date de vérification** : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Statut** : ✅ **CONFIRMÉ - BASE DE DONNÉES UNIQUE**

