# Point technique – Mobility Health

**Date :** 6 février 2025  
**Version API :** 1.0.0

---

## 1. Vue d’ensemble

**Mobility Health** est une plateforme d’assurance voyage / santé avec :
- un **backend API** (FastAPI),
- un **frontend web** (HTML/JS simple + ancien front React/Vite),
- une **application mobile** (Flutter),
- un **module IA** pour l’analyse de documents de souscription.

---

## 2. Architecture technique

### 2.1 Stack globale

| Couche        | Technologie                    | Détails |
|---------------|--------------------------------|--------|
| **Backend**   | Python 3.11, FastAPI 0.104     | API REST, docs Swagger/ReDoc |
| **Base de données** | SQLite (dev) / PostgreSQL 15 (prod) | ORM SQLAlchemy 2.0, migrations Alembic |
| **Cache / files** | Redis 7, MinIO                 | Tâches asynchrones, stockage objets |
| **Tâches async**  | Celery 5.3                     | Workers + Beat (notifications, rappels) |
| **Frontend web**  | HTML/CSS/JS (frontend-simple)  | Multi-pages, pas de build |
| **Frontend “old”**| React 18, Vite 5, TypeScript    | TanStack Query, Formik, Leaflet |
| **Mobile**    | Flutter (SDK ≥3.0)             | Provider + Riverpod, Dio, go_router |

### 2.2 Schéma des composants

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  frontend-simple │   │  frontend.old   │   │  mobile-app     │
│  (HTML/JS)      │   │  (React/Vite)   │   │  (Flutter)      │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   FastAPI (port 8000) │
                    │   /api/v1/*          │
                    │   /health, /docs     │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  PostgreSQL /    │   │  Redis          │   │  MinIO           │
│  SQLite          │   │  (broker Celery) │   │  (fichiers)      │
└─────────────────┘   └────────┬────────┘   └─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Celery Worker + Beat │
                    └──────────────────────┘
```

---

## 3. Backend (FastAPI)

### 3.1 Structure du projet

```
app/
├── main.py              # Point d’entrée, CORS, middlewares, exception handlers
├── api/
│   ├── v1/              # Routes API v1
│   │   ├── auth.py, users.py, products.py, subscriptions.py, voyages.py
│   │   ├── attestations.py, documents.py, invoices.py, payments.py
│   │   ├── sos.py, hospitals.py, finance.py, notifications.py, dashboard.py
│   │   ├── questionnaires.py, destinations.py
│   │   ├── admin_*.py, assureur_*.py, hospital_sinistres.py
│   │   └── ia.py        # Module IA (analyse documents)
│   └── websocket.py
├── core/                # Config, DB, sécurité, Redis, MinIO, Celery
├── models/              # Modèles SQLAlchemy (~35 modèles)
├── schemas/             # Schémas Pydantic
├── services/            # Logique métier (attestations, factures, IA, etc.)
├── middleware/          # Logging, audit
├── ia_module/           # IA : OCR, analyse, formatage par rôle
├── workers/             # Tâches Celery
└── tests/               # Tests pytest
```

### 3.2 Principaux endpoints (préfixe `/api/v1`)

| Domaine        | Préfixe                  | Rôle principal |
|----------------|--------------------------|----------------|
| Auth           | `/auth`                  | Login, refresh, register |
| Utilisateurs   | `/users`                 | CRUD utilisateurs |
| Produits       | `/products`, `/admin/products` | Catalogue, admin |
| Souscriptions  | `/subscriptions`, `/admin/subscriptions` | Souscriptions, admin |
| Voyages        | `/voyages`               | Projets de voyage |
| Attestations   | `/attestations`          | Génération, vérification |
| Documents      | `/documents`             | Upload, URLs présignées |
| Facturation    | `/invoices`              | Factures |
| Paiements      | `/payments`              | Paiements |
| SOS            | `/sos`                   | Alertes, prise en charge |
| Hôpitaux       | `/hospitals`, `/hospital-sinistres` | Partenaires, sinistres |
| Finance        | `/finance`               | Comptabilité |
| Tableau de bord| `/dashboard`             | Stats, indicateurs |
| Sinistres      | `/admin/sinistres`, `/assureur/sinistres` | Admin, assureur |
| Assureurs      | `/assureurs`, `/admin/assureurs`, `/assureur/production` | Partenaires, production |
| Destinations   | `/destinations`          | Pays / zones |
| IA             | `/ia`                    | Analyse de documents (OCR, scoring) |
| Notifications  | `/notifications`         | Notifications utilisateur |

Documentation interactive : `/docs` (Swagger), `/redoc`.

### 3.3 Sécurité et configuration

- **Authentification :** JWT (access + refresh), `python-jose`, `passlib[bcrypt]`.
- **Config :** `pydantic-settings`, fichier `.env` (voir `env.example`).
- **CORS :** En dev, regex sur `localhost` + liste d’origines ; en prod, liste explicite (dont Hostinger, ittechmed).
- **Production :** Vérification de `SECRET_KEY`, interdiction de SQLite, MinIO requis.

**Point d’attention :** Conflit de merge non résolu dans `app/core/config.py` (lignes 82–86) sur `ATTESTATION_VERIFICATION_BASE_URL` — à trancher (srv1324425 vs ittechmed).

---

## 4. Base de données et migrations

- **ORM :** SQLAlchemy 2.0.
- **Migrations :** Alembic (`alembic upgrade head`).
- **Modèles principaux :** `users`, `roles`, `hospitals`, `assureurs`, `produit_assurance`, `souscription`, `projet_voyage`, `attestation`, `sinistre`, `invoice`, `notification`, `ia_analysis`, etc. Détail dans `SCHEMA_DATABASE.md` et `TABLES_BASE_DONNEES.md`.

---

## 5. Module IA

- **Rôle :** Analyse de documents (PDF/images) pour les demandes de souscription.
- **Fonctionnalités :** OCR (Tesseract), extraction d’infos personnelles/médicales, score de risque, détection de fraude/incohérences, formatage selon rôle (assureur, médecin MH, agent technique, agent production).
- **Dépendances :** `pytesseract`, `pdf2image`, `filetype`, `scikit-learn`, `numpy`, `pandas`.
- **Docker :** Image backend avec `tesseract-ocr`, `tesseract-ocr-fra`, `poppler-utils`.

---

## 6. Frontend

### 6.1 frontend-simple (actif)

- **Stack :** HTML, CSS, JavaScript vanilla.
- **Contenu :** Nombreuses pages (login, register, dashboard, produits, souscriptions, attestations, hôpitaux, factures, SOS, admin assureurs/hôpitaux/destinations, etc.) et scripts JS associés dans `js/`.
- **API :** `js/api.js` pour les appels backend.
- **Servi :** Possible via `server.py` ou tout serveur statique.

### 6.2 frontend.old (React/Vite)

- **Stack :** React 18, Vite 5, TypeScript, TanStack React Query, Formik, Yup, Leaflet.
- **Scripts :** `npm run dev`, `npm run build`, tests Jest, Cypress.
- **Statut :** Ancienne version ; le front “officiel” semble être `frontend-simple`.

---

## 7. Application mobile (Flutter)

- **Cible :** Client utilisateur (souscription, attestations, etc.).
- **SDK :** Flutter ≥3.0.
- **State :** Provider, flutter_riverpod.
- **Réseau :** Dio, `connectivity_plus`.
- **Stockage :** `shared_preferences`, `flutter_secure_storage`, Hive.
- **Navigation :** go_router.
- **Config :** `.env` via `flutter_dotenv`.
- **Docs :** Nombreux guides dans `mobile-app/` (installation Flutter, connexion backend, build, etc.).

---

## 8. DevOps et déploiement

### 8.1 Docker

- **docker-compose.yml :**  
  - `db` : PostgreSQL 15 (port 5433),  
  - `redis` : 6379,  
  - `minio` : 9000 (API), 9001 (console),  
  - `api` : FastAPI (8000),  
  - `celery_worker` (queues default, notifications, reminders),  
  - `celery_beat`.
- **Dockerfile :** Python 3.11-slim, dépendances système pour Tesseract/Poppler, `uvicorn` sur 8000.

### 8.2 CI/CD (GitHub Actions)

- **Fichiers :** `.github/workflows/ci.yml`, `deploy.yml`.
- **CI :** Sur push/PR vers `main`/`develop` : tests (PostgreSQL + Redis), flake8 + black (continue-on-error), pytest avec couverture, build Docker, Trivy (sécurité). Codecov optionnel.

### 8.3 Scripts et déploiement

- **Scripts :** `deploy.ps1`, `scripts/` (Python, PowerShell, shell).
- **Doc :** `INSTALL_VPS_MIGRATIONS.md`, `DEMARRAGE_RAPIDE.md`, `DEMARRER_SERVEUR.md`, etc.

---

## 9. Dépendances principales (backend)

| Catégorie     | Paquets |
|---------------|---------|
| API           | fastapi 0.104, uvicorn 0.24, python-multipart |
| DB            | sqlalchemy 2.0.23, alembic 1.12, psycopg2-binary |
| Validation    | pydantic 2.5, pydantic-settings, email-validator |
| Auth          | python-jose[cryptography], passlib[bcrypt], bcrypt |
| Redis / Celery| redis 5.0, celery 5.3, flower 2.0 |
| Stockage      | minio 7.2 |
| PDF / QR      | reportlab, qrcode[pil], Pillow |
| IA            | pytesseract, pdf2image, filetype, scikit-learn, numpy, pandas |
| Tests         | pytest, pytest-cov, pytest-asyncio, httpx |

---

## 10. Points d’attention et recommandations

1. **Conflit de merge :** Résoudre le conflit dans `app/core/config.py` (ATTESTATION_VERIFICATION_BASE_URL).
2. **Double frontend :** Clarifier la cible (frontend-simple vs frontend.old) et, si besoin, documenter la stratégie (migration ou abandon d’un des deux).
3. **CI :** Linter et tests en `continue-on-error: true` — à durcir une fois le code stabilisé.
4. **Sécurité :** Vérifier que Trivy et les bonnes pratiques (secrets, HTTPS, CORS) sont appliqués en production.
5. **Documentation :** `README.md` décrit surtout le backend ; ce point technique complète la vue globale (backend + frontends + mobile + IA + infra).

---

## 11. Références rapides

| Besoin              | Fichier / Commande |
|---------------------|---------------------|
| Démarrer l’API      | `uvicorn app.main:app --reload` |
| Migrations          | `alembic upgrade head` |
| Stack complète      | `docker-compose up` |
| Tests backend       | `pytest app/tests/ -v --cov=app` |
| Docs API            | http://localhost:8000/docs |
| Santé API           | GET /health |
| Schéma BDD          | `SCHEMA_DATABASE.md`, `TABLES_BASE_DONNEES.md` |
| Dépannage           | `TROUBLESHOOTING.md`, `DEPANNAGE_CONNEXION.md` |

---

*Document généré à partir de l’analyse du dépôt Mobility Health.*
