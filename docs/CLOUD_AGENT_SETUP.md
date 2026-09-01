# Configuration Cloud Agent — Mobility Health

## Ce que l'agent Cursor ne peut pas faire pour vous

La configuration du **dashboard Cursor** (connexion GitHub, secrets, premier Build) nécessite votre compte admin sur [cursor.com/dashboard/cloud-agents](https://cursor.com/dashboard/cloud-agents).

## Checklist (15 min)

### 1. Plan Cursor payant

Cloud Agents requiert un plan Pro ou Business.

### 2. Connecter GitHub

1. [cursor.com/dashboard](https://cursor.com/dashboard) → **Integrations**
2. Connecter **GitHub** → autoriser le repo `groupeittech-maker/mobility-health-new`
3. Droits **lecture/écriture** sur le dépôt

### 3. Secrets (onglet Secrets du dashboard)

| Secret | Exemple / usage |
|---|---|
| `SECRET_KEY` | Clé JWT test (32+ caractères) |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/mobility_health_test` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | `localhost:9000` |
| `MINIO_ACCESS_KEY` | `minioadmin` |
| `MINIO_SECRET_KEY` | `minioadmin` |
| `ENVIRONMENT` | `development` |

### 4. Environnement

Le fichier `.cursor/environment.json` à la racine du repo est **déjà commité**.

1. Dashboard → **Cloud Agents** → **Environments**
2. Sélectionner le repo `mobility-health-new`
3. Lancer un **Build** — Cursor exécute `install` (pip install)
4. Attendre le statut **Build active**

### 5. Vérifier dans Cursor Desktop

- Chat agent → menu **Cloud** disponible (non grisé)
- Lancer un agent Cloud sur une tâche test : `cd apps/mhc && pytest app/tests/test_auth.py -v`

## Build test manuel

Après push sur `main` :

1. Dashboard → Builds → **New Build** ou relancer depuis l'environnement
2. Consulter les logs : `pip install -r apps/mhc/requirements.txt` doit réussir
3. Optionnel : agent Cloud exécute les tests listés dans `AGENTS.md`

## Dépannage

| Problème | Solution |
|---|---|
| Cloud grisé | Plan payant + GitHub connecté |
| Build échoue | Vérifier logs install ; Python 3.11 dans `.cursor/Dockerfile` |
| Tests échouent | Ajouter secrets DATABASE_URL, SECRET_KEY, MINIO_* |
| Repo non trouvé | Autoriser `mobility-health-new` dans l'app GitHub Cursor |

## Références

- [Cloud Agent Setup](https://cursor.com/docs/cloud-agent/setup.md)
- [AGENTS.md](../AGENTS.md) — instructions spécifiques MHC
