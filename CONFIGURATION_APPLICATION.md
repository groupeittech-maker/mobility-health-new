# Configuration de l'application Mobility Health Care — Guide étape par étape

Ce guide décrit l'installation complète de la plateforme et la création de tous les profils utilisateurs existants.

---

## Étape 1 — Prérequis

| Outil | Version | Usage |
|---|---|---|
| Docker Desktop | récent | PostgreSQL, Redis, MinIO (et stack complète en option) |
| Python | 3.11 | Backend FastAPI hors Docker |
| Flutter SDK | ≥ 3.0 | Application mobile |
| Git | — | Récupération du code |

---

## Étape 2 — Configuration du backend

### 2.1 Fichier d'environnement

Copier `apps/mhc/env.example` vers `apps/mhc/.env`, puis renseigner :

| Variable | Description | Obligatoire |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./mobility_health.db` (dev) ou `postgresql://user:pass@localhost:5433/mobility_health` | Oui |
| `REDIS_URL` | `redis://localhost:6379/0` — codes de vérification, refresh tokens, broker Celery | Oui |
| `SECRET_KEY` | Clé JWT longue et aléatoire — **rejetée au démarrage si faible en production** | Oui |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Stockage des fichiers (documents, e-cartes, logos) | Oui (prod) |
| `LOCAL_FILE_STORAGE_ROOT` | Repli disque si MinIO indisponible | Recommandé |
| `API_PUBLIC_BASE_URL` | URL publique de l'API (ex. `https://votre-domaine`) — requis pour servir les e-cartes quand MinIO est interne | Prod |
| `ASSURANCE_SITE_WEB` | URL du site web (redirection après vérification e-mail) | Prod |
| `CORS_ORIGINS` | Origines autorisées, séparées par des virgules | Prod |
| `SMTP_*` | Envoi d'e-mails (codes de vérification, notifications) : host, port, security (`ssl`/`starttls`), user, password, from | Recommandé |
| `TWILIO_*` | SMS — optionnel, simulé si absent | Non |
| `FCM_SERVICE_ACCOUNT_PATH` ou `FCM_SERVICE_ACCOUNT_JSON` + `FCM_PROJECT_ID` | Notifications push mobile (Firebase HTTP v1) | Mobile |
| `*_SERVICE_MODE` (`PAYMENT`, `OCR`, `TRUST`, `EKYC`) | `stub` (simulation locale) ou `live` (services IT-Tech externes) + `*_SERVICE_URL` / clés | stub par défaut |
| `EKYC_WEBHOOK_SECRET` | Vérification des signatures des webhooks eKYC | Si eKYC live |

### 2.2 Démarrer l'infrastructure

```bash
cd apps/mhc
docker compose up -d db redis minio
```

Services : PostgreSQL (port externe **5433**), Redis (6379), MinIO (API 9000, console 9001).

### 2.3 Installer les dépendances et migrer la base

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 2.4 Lancer l'API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Vérification : `http://localhost:8000/health` et `http://localhost:8000/docs`.

### 2.5 Workers Celery (notifications, rappels)

```bash
celery -A app.core.celery_app:celery_app worker --loglevel=info --queues=default,notifications,reminders
celery -A app.core.celery_app:celery_app beat --loglevel=info
```

> Alternative tout-en-un : `docker compose up -d` démarre db + redis + minio + api + celery_worker + celery_beat. Sous Windows, le script `scripts\start_all_services.ps1` lance dépendances + backend + frontend + workers.

---

## Étape 3 — Données de référence (à charger une fois)

```bash
cd apps/mhc

# Pays et villes de destination (référentiel mondial)
python scripts/init_destinations.py

# Hôpitaux partenaires avec coordonnées GPS (à adapter dans le script)
python scripts/seed_hospitals.py

# Assureurs et produits d'assurance de démonstration
python scripts/create_assureurs_and_products.py
```

Puis dans le portail **admin** :
1. **Tarification** : rattacher les pays aux zones tarifaires (`INTRA_AFRIQUE`, `RSA_MAGHREB`, `EXTRA_AFRIQUE`, `INTER_AFRIQUE`, `FRANCE_UE`), définir fenêtres de durée, tranches d'âge, grilles de prix.
2. **Frais & taxes** : paramétrer frais de service et taxes par pays assureur.
3. **Produits** : créer/vérifier les produits, leurs garanties, zones, âges min/max, durée max.
4. **Assureurs / Courtiers** : créer les partenaires, logos, commissions.
5. **Destinations** : activer les pays vendables.

---

## Étape 4 — Compte administrateur

```bash
python scripts/create_admin_sql.py
```

Crée `admin` / `admin123` (à changer immédiatement). Alternative : `scripts/create_test_users.py` crée un jeu complet de comptes de test pour tous les rôles.

---

## Étape 5 — Frontend web

```powershell
scripts\start_frontend.ps1    # sert frontend-simple sur http://localhost:3000
```

La page `login.html` redirige automatiquement chaque rôle vers son portail.

---

## Étape 6 — Application mobile

```bash
cd apps/mhc/mobile-app
Copy-Item .env.example .env    # ou scripts create_env.ps1 / create_env.sh
```

Renseigner `API_BASE_URL` selon la cible :

| Cible | Valeur |
|---|---|
| Émulateur Android | `http://10.0.2.2:8000/api/v1` |
| Simulateur iOS | `http://localhost:8000/api/v1` |
| Appareil physique | `http://<IP-de-la-machine>:8000/api/v1` |
| Production | `https://votre-domaine/api/v1` |

```bash
flutter pub get
flutter run
```

Profils mobiles : **assuré** (souscription, SOS, attestations) et **médecin référent MH** (pipeline sinistre). Les autres profils passent par le web.

---

## Étape 7 — Création des profils utilisateurs

### 7.1 Trois méthodes de création

| Méthode | Pour qui | Comment |
|---|---|---|
| **Auto-inscription** | Assuré (`user`) | Page `register.html` ou mobile → code e-mail à 6 chiffres → compte activé immédiatement (pas d'approbation humaine) |
| **Portail admin** | Tous les autres profils | `admin-users.html` → création avec choix du rôle (+ hôpital le cas échéant) → e-mail de bienvenue envoyé |
| **Script** | Jeu de test | `scripts/create_test_users.py` |

Un compte créé par l'admin est **actif immédiatement** (`email_verified` et `validation_inscription=approved` posés d'office).

### 7.2 Les 18 profils et leurs prérequis de configuration

#### Profils internes Mobility Health — simple création (rôle seul)

| Rôle | Portail web après login | Fonction |
|---|---|---|
| `admin` | `admin-dashboard.html` | Administration complète |
| `medical_reviewer` | `medical-review.html` | Revue médicale des dossiers, validation des factures médicales |
| `doctor` | `hospital-doctor.html` | Médecin MH (validations médicales) |
| `technical_reviewer` | `technical-review.html` | Revue technique (rôle legacy — les dossiers techniques sont désormais traités par la production) |
| `production_agent` | `production-review.html` | Décision finale dossiers, résiliations, souscription pour tiers |
| `sos_operator` | `sos-dashboard.html` | Centre SOS temps réel, validation « sinistre » des factures |
| `agent_sinistre_mh` | `sinistre-invoices.html` | Gestion des sinistres, validation « sinistre » des factures |
| `medecin_referent_mh` | `medical-review.html` + **mobile** | Vérification des alertes, validation rapports et factures |
| `finance_manager` | `accounting-portal.html` | Validation comptable, répartitions |
| `agent_comptable_mh` | `accounting-portal.html` | Comptabilité MH |

#### Profils hôpital — création + rattachement obligatoire à un hôpital

Ces comptes **doivent avoir `hospital_id` renseigné** (champ hôpital dans la fiche utilisateur admin), sinon l'accès est refusé (« aucun hôpital n'est associé à votre compte »). L'hôpital doit exister au préalable (`admin-hospitals.html` ou `seed_hospitals.py`).

| Rôle | Portail | Fonction |
|---|---|---|
| `hospital_admin` | `hospital-dashboard.html` | Admin établissement, tarifs, séjours, factures |
| `agent_reception_hopital` | `hospital-reception.html` | Accueil sinistré, ambulance, ouverture du séjour |
| `medecin_hopital` | `hospital-doctor.html` | Rapport médical du séjour |
| `agent_comptable_hopital` | `hospital-dashboard.html` | Émission des factures |

> Un hôpital peut aussi désigner un **médecin référent MH** (`medecin_referent_id` sur la fiche hôpital) — il est alors assigné en priorité aux sinistres de cet hôpital.

#### Profils assureur — création + rattachement via la fiche assureur

Créer le compte utilisateur, puis le **rattacher dans `admin-assureurs.html`** : chaque assureur a trois listes d'agents — **comptable**, **production**, **sinistre** (table `assureur_agents`).

| Rôle | Type d'agent à rattacher | Portail | Fonction |
|---|---|---|---|
| `agent_comptable_assureur` | comptable | `assureur-accounting.html` | Comptabilité de l'assureur |
| `agent_sinistre_assureur` | sinistre | `sos-dashboard.html` | Sinistres + décision des suspensions/réémissions de police |
| `production_agent` | production | `production-review.html` | Vue production côté assureur |

#### Profil courtier — création + rattachement via la fiche courtier

| Rôle | Rattachement | Portail | Fonction |
|---|---|---|---|
| `agent_comptable_courtier` | Champ **agent comptable** sur la fiche courtier (`admin-courtiers.html`, courtier lui-même rattaché à un assureur avec sa commission %) | `assureur-accounting.html` | Comptabilité/commissions du courtier |

#### Profil assuré

| Rôle | Création | Accès |
|---|---|---|
| `user` | Auto-inscription uniquement (pas de création admin nécessaire) | `user-dashboard.html` + mobile |

### 7.3 Récapitulatif des dépendances de configuration par profil

```
Admin crée d'abord :
  ├── Hôpital            → puis comptes hospital_admin / réception / médecin / comptable (hospital_id)
  │                        → puis médecin référent de l'hôpital (medecin_referent_id)
  ├── Assureur           → puis comptes agents (comptable / sinistre / production) rattachés
  │     └── Courtier     → rattaché à un assureur → compte agent_comptable_courtier lié
  ├── Produits + tarification → zones, prix, taxes
  └── Comptes internes MH → aucun rattachement requis
```

---

## Étape 8 — Services externes (optionnel, modes stub → live)

| Service | Mode `stub` (défaut) | Mode `live` |
|---|---|---|
| Paiement (`PAYMENT_SERVICE_*`) | Orchestrateur simulé, checkout interne | API orchestrateur IT-Tech (URL + API key) |
| OCR (`OCR_SERVICE_*`) | Tesseract local | API OCR externe |
| Trust (`TRUST_SERVICE_*`) | No-op | Signature/horodatage des documents |
| eKYC (`EKYC_SERVICE_*`) | Sessions simulées | Vérification d'identité réelle + webhooks signés (`EKYC_WEBHOOK_SECRET`) |

Ne jamais appeler Tesseract ou un PSP directement : toujours passer par les clients d'intégration (`get_*_client()`).

---

## Étape 9 — Vérification finale

```bash
# Santé API
curl http://localhost:8000/health

# Tests
pytest app/tests/ -v

# Stack complète
docker compose ps
```

Checklist fonctionnelle :
1. Login admin → création d'un utilisateur de chaque profil
2. Auto-inscription d'un assuré → code e-mail → connexion
3. Parcours souscription complet jusqu'à l'attestation
4. Alerte SOS de test → vérifier la notification du référent et de la réception hôpital
5. Rapport → facture → 3 validations → alerte résolue
