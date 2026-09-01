# Fiche technique — Mobility Health Care

**Date :** 30 juillet 2026
**Version API :** 1.0.0
**Version mobile :** 1.0.0+2

---

## 1. Présentation générale

**Mobility Health Care** est une plateforme complète d'**assurance voyage santé** couvrant l'intégralité du cycle de vie d'un contrat :

> Souscription (devis tarifié) → Questionnaires (administratif / médical) → Paiement → Attestation & e-carte → Alerte SOS / sinistre hospitalier → Facturation multi-validation → Répartition financière (assureur / courtier / MH)

La solution se compose de :

- un **backend API REST** (FastAPI) avec WebSockets temps réel,
- un **frontend web multi-portails** (HTML/CSS/JS vanilla) couvrant une quinzaine de rôles,
- une **application mobile Flutter** (assuré + médecin référent MH),
- un **module IA** d'analyse de documents de souscription (OCR, scoring),
- une **infrastructure conteneurisée** (Docker Compose, Nginx, VPS).

---

## 2. Stack technique

### 2.1 Backend

| Couche | Technologie | Version |
|---|---|---|
| Langage | Python | 3.11 (`python:3.11-slim`) |
| Framework API | FastAPI | 0.104.1 |
| Serveur ASGI | Uvicorn | 0.24.0 |
| Validation | Pydantic / pydantic-settings | 2.5.0 / 2.1.0 |
| ORM | SQLAlchemy | 2.0.23 |
| Migrations | Alembic | 1.12.1 (~68 révisions) |
| Base de données (prod) | PostgreSQL | 15 (`postgres:15-alpine`) |
| Base de données (dev) | SQLite | fichier local |
| Cache / broker | Redis | 7 (client 5.0.1) |
| Tâches asynchrones | Celery + Flower | 5.3.4 / 2.0.1 |
| Stockage objets | MinIO (S3-compatible) | SDK 7.2.0 |
| Authentification | python-jose (JWT) + passlib/bcrypt | 3.3.0 / 1.7.4 |
| Génération PDF | ReportLab | 4.0.7 |
| QR codes / images | qrcode / Pillow | 7.4.2 / 10.1.0 |
| Notifications push | firebase-admin (FCM HTTP v1) | 6.5.0 |
| IA / OCR | pytesseract, pdf2image, scikit-learn, pandas, numpy | voir `requirements.txt` |

### 2.2 Frontend web (`frontend-simple/`)

- **HTML + CSS + JavaScript vanilla**, multi-pages, sans étape de build.
- Appels API centralisés dans `js/api.js`.
- Servi via Nginx (prod) ou serveur statique (dev).

### 2.3 Application mobile (`mobile-app/`)

- **Flutter** (SDK ≥ 3.0 < 4.0), package `mobility_health_mobile`.
- État : Provider + Riverpod — Navigation : go_router — HTTP : Dio.
- Stockage : shared_preferences, flutter_secure_storage, Hive.
- Push : firebase_core, firebase_messaging, notifications locales, badge.
- Autres : géolocalisation, image/file picker, visionneuse PDF (`pdfx`).

---

## 3. Architecture des composants

```
┌──────────────────┐        ┌──────────────────┐
│  frontend-simple  │        │   mobile-app     │
│  (HTML/JS)        │        │   (Flutter)      │
└─────────┬────────┘        └────────┬─────────┘
          │                          │
          └────────────┬─────────────┘
                       ▼
          ┌─────────────────────────┐
          │  FastAPI (port 8000)     │
          │  /api/v1/*  /ws/sos      │
          │  /docs  /redoc  /health  │
          └────────────┬────────────┘
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ PostgreSQL │  │   Redis    │  │   MinIO    │
│  15        │  │ (broker)   │  │ (fichiers) │
└────────────┘  └─────┬──────┘  └────────────┘
                      ▼
          ┌─────────────────────────┐
          │  Celery Worker + Beat    │
          │  (default, notifications,│
          │   reminders)             │
          └─────────────────────────┘
```

---

## 4. Modules API (préfixe `/api/v1`)

| Module | Rôle |
|---|---|
| `auth` | Inscription, login/refresh/logout, profil, token FCM, reset mot de passe, vérification e-mail |
| `users` | CRUD utilisateurs (admin), profils liés hôpital |
| `products` / `admin/products` | Catalogue public, devis / calcul de prime, administration produits et tarifs |
| `admin/tarification` | Référentiels zones, fenêtres de durée, tranches d'âge, grilles de prix |
| `subscriptions` / `admin/subscriptions` | Parcours souscription assuré et supervision admin |
| `voyages` | Projets de voyage + upload des pièces justificatives |
| `questionnaires` | Questionnaires courts/longs, administratifs et médicaux |
| `payments` | Initiation, checkout, confirmation, webhook, statut, journal comptable |
| `attestations` | Attestations PDF / e-carte, circuit de validation, vérification publique |
| `documents` | Consultation et téléchargement des documents des dossiers |
| `sos` | Alertes SOS, sinistres, workflow, temps réel WebSocket |
| `hospitals` / `hospital-sinistres` | Réseau hospitalier, tarifs examens/actes, prestations, séjours, rapports |
| `admin/sinistres` / `assureur/sinistres` | Gestion des sinistres côté MH et côté assureur |
| `finance` | Comptes, mouvements, répartitions, remboursements |
| `invoices` | Factures sinistre + validations médicale / sinistre / comptable |
| `notifications` | Notifications in-app (liste, marquage lu) |
| `dashboard` | Agrégats et indicateurs des tableaux de bord |
| `admin/assureurs` / `assureurs` | CRUD assureurs partenaires, agents, logos |
| `admin/courtiers` / `courtiers` | CRUD courtiers (commission, rattachement assureur) |
| `assureur/production` | Vue production / souscriptions côté assureur |
| `destinations` | Référentiel pays/villes de destination (avec synchronisation) |
| `ia` | Analyse OCR/IA des documents de souscription |

**Documentation interactive :** `/docs` (Swagger) et `/redoc`.
**Temps réel :** WebSocket `/ws/sos` (opérateurs SOS, agents sinistre, médecins, admin).

---

## 5. Modèle de données (principaux modèles SQLAlchemy)

| Domaine | Modèles |
|---|---|
| Utilisateurs | `User`, `RoleModel`, `ContactProche` |
| Partenaires | `Assureur`, `AssureurAgent`, `Courtier` |
| Produits & tarification | `ProduitAssurance`, `ProduitPrimeTarif`, `HistoriquePrix`, `TarificationZone`, `ZonePays`, `FenetreDuree`, `GrillePrix`, `TrancheAge`, `GrilleFinale` |
| Souscription | `ProjetVoyage`, `ProjetVoyageDocument`, `Souscription`, `Questionnaire` |
| Paiements | `Paiement`, `TransactionLog` |
| Attestations | `Attestation`, `ValidationAttestation` |
| Hôpitaux & soins | `Hospital`, `HospitalStay`, `HospitalExamTarif`, `HospitalActTarif`, `Prestation`, `Rapport` |
| Sinistres | `Alerte`, `Sinistre`, `SinistreProcessStep`, `Invoice`, `InvoiceItem` |
| Finance | `Account`, `Movement`, `Repartition`, `Refund` |
| Référentiels | `DestinationCountry`, `DestinationCity` |
| Système | `Notification`, `AuditLog`, `IAAnalysis`, `FailedTask` |

**Rôles applicatifs :** `admin`, `user` (assuré), `doctor`, `hospital_admin`, `agent_reception_hopital`, `medecin_hopital`, `medecin_referent_mh`, `medical_reviewer`, `technical_reviewer`, `production_agent`, `sos_operator`, `agent_sinistre_mh`, `agent_sinistre_assureur`, `finance_manager`, agents comptables (MH / assureur / courtier / hôpital), `courtier`.

---

## 6. Services métiers (`app/services/`)

| Service | Rôle |
|---|---|
| `attestation_service` | Cycle de vie des attestations (provisoire/définitive), e-carte |
| `pdf_service` | Génération PDF des attestations (ReportLab + QR) |
| `card_service` | Génération de l'image e-carte (Pillow) |
| `prime_tarif_service` / `voyage_premium_calculator` | Calcul de prime et frais de services (grilles de coefficients) |
| `produit_selection_assureur` | Filtrage des produits selon le territoire de l'assureur |
| `finance_service` | Mouvements, soldes, répartitions financières |
| `notification_service` / `fcm_push` | Notifications multi-canal (in-app, e-mail, SMS, push FCM v1) |
| `minio_service` / `project_document_storage` | Stockage fichiers (MinIO + repli disque local) |
| `sinistre_workflow_service` | Étapes du workflow sinistre |
| `ia_auto_service` | Orchestration des analyses IA de documents |
| `destination_reference` / `country_reference` | Synchronisation des référentiels pays/villes |
| `user_service`, `invoice_history`, `qrcode_service`, `referent_notification_reads` | Utilisateurs, historique factures, QR, suivi lecture notifications |

---

## 7. Portails web par rôle

| Portail | Pages principales |
|---|---|
| Public / Assuré | index, login, register, vérification e-mail, dashboard, sélection produit, assistant projet voyage, souscription, questionnaires, paiement, attestations |
| Admin MH | dashboard, utilisateurs, produits, tarification, souscriptions, assureurs, courtiers, hôpitaux, destinations, attestations |
| Circuit de validation | revue médicale, revue technique, revue production |
| Hôpital | dashboard, réception (+ carte), médecin (+ rapport), factures, détails alerte |
| SOS / Sinistre | dashboard SOS, carte des alertes, factures sinistre |
| Comptabilité | portail comptable, grand livre, dashboard finance, comptabilité assureur |
| Assureur | production, sinistres, comptabilité |

La redirection post-login est gérée par rôle dans `js/login.js`.

---

## 8. Application mobile — périmètre

1. **Assuré (`user`)** : tableau de bord, parcours de souscription complet (produit → voyage → questionnaire médical → paiement → attestation), déclenchement d'**alerte SOS géolocalisée**, historique, attestations, profil.
2. **Médecin référent MH (`medecin_referent_mh`)** : pipeline de dossiers, détail dossier et facture, notifications push (SOS, rapports, factures), profil.

---

## 9. Notifications, paiements, documents

### Notifications (multi-canal)
- **In-app** : table `Notification` + API dédiée.
- **E-mail** : SMTP (STARTTLS/SSL) avec retries via Celery.
- **SMS** : Twilio (optionnel, simulé si non configuré).
- **Push** : FCM HTTP v1 (compte de service Firebase), token stocké sur l'utilisateur.

### Paiements
- Flux de checkout interne avec webhook générique (pas de PSP externe branché à ce jour).
- Types supportés : carte bancaire, virement, **Mobile Money (Airtel, MTN, Orange, Moov)**, paiement différé, prélèvement, espèces, chèque.

### Documents et attestations
- Stockage MinIO avec URLs présignées + repli disque local (`LOCAL_FILE_STORAGE_ROOT`).
- Attestation provisoire → circuit de validation (médical → technique → production) → attestation définitive + e-carte.
- Vérification publique par QR code : `/api/v1/attestations/verify/{numero}`.

---

## 10. Tâches asynchrones (Celery)

Broker et backend : **Redis**. Queues : `default`, `notifications`, `reminders`.

| Tâche | Fonction |
|---|---|
| `send_email` / `send_sms` / `send_push` | Envois avec retries |
| `send_notification_multi_channel` | Orchestration multi-canal |
| `schedule_questionnaire_reminder` / `send_questionnaire_reminder` | Rappels de questionnaires |
| `process_questionnaire_reminders` | Beat quotidien (09:00 UTC) |
| `process_pending_notifications` | Traitement de la file de notifications |
| `retry_failed_tasks` | Beat toutes les 10 minutes |
| `record_failed_task` | Persistance des échecs (`FailedTask`) |

---

## 11. Sécurité

- **Mots de passe** : hachage bcrypt (passlib).
- **JWT HS256** : access token (~30 min), refresh token (~7 jours), tokens spécialisés (e-carte, téléchargement, activation d'inscription, vérification e-mail).
- **OAuth2 password bearer** sur `/api/v1/auth/login`.
- **Codes temporaires** (reset mot de passe, vérification e-mail) stockés dans Redis.
- **Garde-fous production** : rejet au démarrage si `SECRET_KEY` faible, SQLite ou MinIO non configuré.
- **Audit** : middleware de journalisation HTTP (`AuditLog`, requête/réponse).
- **CORS** : regex localhost en dev, liste explicite en production.

---

## 12. Infrastructure et déploiement

### Conteneurs (Docker)
- `Dockerfile` (dev, hot-reload) et `Dockerfile.prod` (image figée) : Python 3.11-slim + Tesseract OCR (fra) + Poppler.
- `docker-compose.yml` : `db` (PostgreSQL 15, port 5433), `redis` (6379), `minio` (9000/9001), `api` (8000), `celery_worker`, `celery_beat`.
- `docker-compose.prod.yml` : équivalent production (volumes uploads, secret FCM, sans `--reload`).

### Serveur & réseau
- **Nginx** en frontal : service du frontend statique, proxy `/api` vers FastAPI, HTTPS Let's Encrypt (configs dans `deploy/nginx/`).
- Hébergement : VPS Hostinger (`srv1324425.hstgr.cloud`), domaine `mobility-health.ittechmed.com`.
- Scripts de déploiement : `deploy.ps1`, `deploy/deploy-scp.ps1` et scripts ciblés (voir `deploy/README-DEPLOY.md`).

### Variables d'environnement clés (`env.example`)
`DATABASE_URL`, `REDIS_URL`, `MINIO_*`, `LOCAL_FILE_STORAGE_ROOT`, `API_PUBLIC_BASE_URL`, `SECRET_KEY`, durées JWT, `ENVIRONMENT`, `CORS_ORIGINS`, `SMTP_*`, `TWILIO_*`, `FCM_SERVICE_ACCOUNT_*` / `FCM_PROJECT_ID`.

---

## 13. Références rapides

| Besoin | Commande / fichier |
|---|---|
| Démarrer l'API (dev) | `uvicorn app.main:app --reload` |
| Stack complète | `docker-compose up` |
| Migrations | `alembic upgrade head` |
| Tests backend | `pytest app/tests/ -v --cov=app` |
| Docs API | `http://localhost:8000/docs` |
| Santé API | `GET /health` |
| Point technique détaillé | `POINT_TECHNIQUE.md` |
| Installation BDD VPS | `INSTALL_BD_VPS.md` |

---

*Fiche technique générée à partir de l'analyse du dépôt Mobility Health Care.*
