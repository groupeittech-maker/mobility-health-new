# Mobility Health Care — instructions agents

## Structure monorepo

- `apps/mhc/` — application principale (backend FastAPI, frontend-simple, mobile Flutter)
- `contracts/` — contrats API des services IT-Tech externes
- `deploy/` — scripts et configs déploiement VPS

## Backend MHC

```bash
cd apps/mhc
pip install -r requirements.txt
docker compose up -d
alembic upgrade head
pytest app/tests/ -v
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Variables : copier `apps/mhc/env.example` vers `apps/mhc/.env`.

## Intégrations services externes

Couche `app/integrations/` — modes `stub` (défaut) ou `live` via `.env` :

- `PAYMENT_SERVICE_MODE` — AfriPaie (orchestrateur, `PAYMENT_SERVICE_URL=https://afripaie.online`,
  clé `sk_test_…`/`sk_live_…` dans `PAYMENT_SERVICE_API_KEY`, secret webhook `whsec_…`
  dans `PAYMENT_SERVICE_WEBHOOK_SECRET` — voir `contracts/payment-api.v1.md`)
- `OCR_SERVICE_MODE` — phase 2
- `TRUST_SERVICE_MODE` — phase 3
- `MESSAGING_SERVICE_MODE` — SMS/WhatsApp (codes de vérification MyMHC)

MHC ne doit pas appeler directement Tesseract ou un PSP : passer par `get_*_client()`.

## Cursor Cloud specific instructions

1. **Répertoire de travail** : `apps/mhc` pour le backend, tests et Docker.
2. **Tests** :
   ```bash
   cd apps/mhc
   export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mobility_health_test
   export REDIS_URL=redis://localhost:6379/0
   export SECRET_KEY=test-secret-key-for-ci
   export MINIO_ENDPOINT=localhost:9000
   export MINIO_ACCESS_KEY=minioadmin
   export MINIO_SECRET_KEY=minioadmin
   docker compose up -d db redis minio
   alembic upgrade head
   pytest app/tests/ -v --tb=short
   ```
3. **Secrets Cloud Agent** (dashboard Cursor → Secrets) :
   - `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `MINIO_*`
   - `PAYMENT_SERVICE_*`, `OCR_SERVICE_*`, `TRUST_SERVICE_*` (quand live)
4. **Ne pas committer** : `.env`, secrets Firebase, clés API production.
5. **Déploiement production** : manuel via `deploy.ps1` ou GitHub Actions — pas depuis Cloud Agent par défaut.

Voir `docs/CLOUD_AGENT_SETUP.md` pour la configuration dashboard.

## Workflow MyMHC V3 (actions sur une police, documents)

- Actions police : `app/services/avenant_service.py` + `app/api/v1/avenants.py`
  (`/subscriptions/{id}/actions[/annulation|/modification|/prorogation]`, `confirmer=false` = simulation).
  Une seule demande en cours par attestation (statut avenant `attente_paiement`). Suspension / réémission supprimées.
- Nomenclature (`app/core/mhc_nomenclature.py`) : 102 annulation, 107 modification, 108 prorogation,
  119 quittance de règlement, 120 quittance de ristourne. Numéro définitif attribué à l'émission (`PROV-…` avant).
- Ristournes (`app/models/ristourne.py`) : calculées « à rembourser », confirmées par la finance
  (fonctionnalité `remboursement`, `finance-outbound.html#remboursements`) → quittance 120.
- Durée max voyage : `MAX_TRIP_DAYS = 92` (`app/core/constants.py`).
- Tests ciblés rapides : `pytest app/tests/test_avenants.py app/tests/test_subscription_decision.py app/tests/test_subscription_cleanup.py -q --no-cov`
  (`--no-cov` évite l'échec `fail-under=90` sur un sous-ensemble).
