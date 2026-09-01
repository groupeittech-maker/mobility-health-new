# Commandes SCP manuelles

Référence détaillée : **`deploy/SCP-DEPLOY-CHEMINS.md`** (structure réelle srv1324425).

| Cible | Chemin |
|--------|--------|
| **Frontend** | `scp … frontend-simple` vers **`/var/www/mobility-health/`** → `frontend-simple/` *(symlink vers `Mobility Health` avec espace)* |
| **Backend (Docker)** | **`/var/www/Mobility_Health/Mobility_Health/`** *(underscore ; ne pas confondre avec `Mobility Health`)* |

> Si l’arborescence change : `ls -la /var/www/` et lire la section 1 de `SCP-DEPLOY-CHEMINS.md`.

À exécuter **depuis la racine du projet** (dossier contenant `app`, `frontend-simple`).

**Variables utiles :**

```powershell
$H = "root@srv1324425.hstgr.cloud"
```

Créer les dossiers si besoin (une fois) :

```powershell
ssh $H "mkdir -p /var/www/mobility-health/frontend-simple /var/www/Mobility_Health/Mobility_Health"
```

---

## Frontend

```powershell
scp -r -o StrictHostKeyChecking=no frontend-simple "${H}:/var/www/mobility-health/"
```

→ `/var/www/mobility-health/frontend-simple/`

---

## Backend

```powershell
scp -r -o StrictHostKeyChecking=no app alembic "${H}:/var/www/Mobility_Health/Mobility_Health/"
scp -o StrictHostKeyChecking=no docker-compose.yml docker-compose.prod.yml Dockerfile Dockerfile.prod requirements.txt alembic.ini "${H}:/var/www/Mobility_Health/Mobility_Health/"
```

---

## Bloc tout-en-un

```powershell
$H = "root@srv1324425.hstgr.cloud"
ssh $H "mkdir -p /var/www/mobility-health/frontend-simple /var/www/Mobility_Health/Mobility_Health"
scp -r -o StrictHostKeyChecking=no frontend-simple "${H}:/var/www/mobility-health/"
scp -r -o StrictHostKeyChecking=no app alembic "${H}:/var/www/Mobility_Health/Mobility_Health/"
scp -o StrictHostKeyChecking=no docker-compose.yml docker-compose.prod.yml Dockerfile Dockerfile.prod requirements.txt alembic.ini "${H}:/var/www/Mobility_Health/Mobility_Health/"
```

---

## Après la copie (SSH)

```bash
ssh root@srv1324425.hstgr.cloud
cd /var/www/Mobility_Health/Mobility_Health
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache api
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api
systemctl reload nginx
```

---

## Alignement avec `deploy.ps1`

Les variables `$SERVER_FRONTEND` et `$SERVER_BACKEND` en tête de **`deploy.ps1`** doivent correspondre aux chemins ci-dessus (c’est le cas par défaut dans le dépôt).
