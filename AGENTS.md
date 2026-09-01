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

- `PAYMENT_SERVICE_MODE` — phase 4
- `OCR_SERVICE_MODE` — phase 2
- `TRUST_SERVICE_MODE` — phase 3

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
