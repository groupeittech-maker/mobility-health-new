# IT-Tech Platform — Mobility Health

Monorepo de la plateforme **Mobility Health Care** et des contrats d'intégration vers les services IT-Tech.

## Structure

```
├── apps/mhc/              # Application MHC (backend, web, mobile)
├── contracts/             # Contrats API Payment, OCR, Trust
├── deploy/                # Scripts déploiement VPS
├── docs/                  # Documentation (Cloud Agent, etc.)
├── .cursor/               # Configuration Cloud Agent Cursor
└── .github/workflows/     # CI/CD
```

## Démarrage

```bash
cd apps/mhc
docker compose up -d
```

Voir [apps/mhc/README.md](apps/mhc/README.md).

## Cloud Agent Cursor

1. Push sur GitHub
2. Configurer le dashboard : [docs/CLOUD_AGENT_SETUP.md](docs/CLOUD_AGENT_SETUP.md)
3. Fichier `.cursor/environment.json` déjà présent

## CI/CD

- **CI** : push/PR sur `main` ou `develop` → tests pytest + build Docker
- **Deploy** : push `main` ou manuel → VPS Hostinger (`deploy.yml` / `deploy.ps1`)

## Roadmap services externes

| Phase | Service | Statut |
|---|---|---|
| 1 | Finaliser MHC Core | En cours |
| 2 | OCR/HTR Service | À créer |
| 3 | Digital Trust | À créer |
| 4 | Payment Orchestrator (intégration) | Existant — branchement |
| — | Flutter mobile | Conservé |
