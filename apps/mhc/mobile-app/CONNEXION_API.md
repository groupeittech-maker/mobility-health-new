# Connexion aux API - Application Mobile Mobility Health

## Configuration

### 1. Fichier `.env`

Le fichier `.env` à la racine de `mobile-app/` doit contenir :

```env
# API Backend - Production
API_BASE_URL=https://api.srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://api.srv1324425.hstgr.cloud

API_TIMEOUT=30000
ENVIRONMENT=production
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

### 2. Environnements

| Environnement | API_BASE_URL |
|---------------|--------------|
| **Production** | `https://api.srv1324425.hstgr.cloud/api/v1` |
| **Local (émulateur Android)** | `http://10.0.2.2:8000/api/v1` |
| **Local (appareil réel)** | `http://<IP_PC>:8000/api/v1` |

## APIs connectées

| Service | Endpoints | Usage |
|---------|-----------|-------|
| **Auth** | `/auth/login`, `/auth/register`, `/auth/me`, `/auth/refresh`, `/auth/logout` | Connexion, inscription, profil |
| **Produits** | `GET /products/`, `GET /products/:id` | Liste et détail des produits |
| **Souscriptions** | `GET /subscriptions/`, `POST /subscriptions/start` | Liste et création |
| **Voyages** | `GET /voyages/`, `POST /voyages/` | Projets de voyage |
| **SOS** | `POST /sos/trigger`, `GET /sos/` | Déclencher alerte, liste alertes |
| **Attestations** | `GET /users/me/attestations`, `GET /subscriptions/:id/attestations` | Attestations utilisateur |
| **Paiements** | `POST /payments/initiate`, `GET /payments/:id/status` | Initier et suivre paiement |
| **Questionnaires** | `POST /subscriptions/:id/questionnaire/medical`, etc. | Soumission questionnaires |
| **Destinations** | `GET /destinations/countries`, `GET /destinations/countries/:id/cities` | Pays et villes |
| **Assureurs** | `GET /assureurs` | Partenaires assurance (logos) |
| **Hospital-stays** | `GET /hospital-sinistres/hospital-stays` | Historique hospitalisations |

## Authentification

- **Login** : Token stocké dans `FlutterSecureStorage` (access_token, refresh_token)
- **Requêtes** : Le `ApiClient` ajoute automatiquement le header `Authorization: Bearer <token>`
- **Refresh** : En cas de 401, le client tente un refresh du token via `/auth/refresh`

## Vérifier la connexion

1. Lancer l'app : `flutter run`
2. Se connecter avec un compte valide
3. Le tableau de bord charge les souscriptions et attestations depuis l'API
