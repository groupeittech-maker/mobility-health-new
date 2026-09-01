# Mobility Health Care (MHC)

Application principale — assurance voyage santé.

## Contenu

| Dossier | Description |
|---|---|
| `app/` | Backend FastAPI |
| `frontend-simple/` | Portails web HTML/JS |
| `mobile-app/` | Application Flutter (assuré + médecin référent) |
| `alembic/` | Migrations base de données |

## Démarrage rapide

```bash
cd apps/mhc
cp env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
```

API : http://localhost:8000/docs

## Intégrations services externes

Couche `app/integrations/` — variables dans `.env` :

- `PAYMENT_SERVICE_MODE=stub|live` (phase 4)
- `OCR_SERVICE_MODE=stub|live` (phase 2)
- `TRUST_SERVICE_MODE=stub|live` (phase 3)

Contrats API : `../../contracts/`

## Déploiement production

Depuis la racine du monorepo :

```powershell
.\deploy.ps1
```
