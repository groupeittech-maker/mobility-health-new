# Déploiement SCP – Chemins serveur

**Référence Hostinger (srv1324425)** : structure constatée sur le VPS (mars 2026). Les scripts `deploy.ps1`, `deploy/SCP-COMMANDES-MANUEL.md` et `deploy/deploy-scp.ps1` s’y alignent.

## 1. Arborescence réelle sous `/var/www/`

```
/var/www/
├── mobility-health          → lien symbolique vers …/Mobility_Health/Mobility Health  (avec un **espace** dans le nom)
├── Mobility_Health/         (dossier, underscore)
│   ├── Mobility Health/     ← cible du symlink (fichiers HTML à la racine, sous-dossier frontend-simple, etc.)
│   └── Mobility_Health/     ← **backend API / Docker** (docker-compose, app, alembic, .env) — **sans espace**
├── certbot/
└── html/
```

### À ne pas confondre

| Chemin | Rôle |
|--------|------|
| **`/var/www/Mobility_Health/Mobility Health`** (espace) | Site statique accessible via **`/var/www/mobility-health`** (symlink). Peut contenir d’anciens dossiers (`app`, `backend`, …) : **ce n’est pas** le répertoire où lancer `docker compose` pour l’API actuelle. |
| **`/var/www/Mobility_Health/Mobility_Health`** (underscore) | **Projet backend** : `docker compose`, `app/`, `alembic/`, `.env`. C’est **`cd` ici** pour rebuild / migrations. |

---

## 2. Chemins retenus pour la copie

| Cible | Chemin d’usage | Détail |
|--------|----------------|--------|
| **Frontend** | `/var/www/mobility-health/` (recommandé) | Même répertoire physique que `…/Mobility_Health/Mobility Health/`. Après `scp -r frontend-simple …/mobility-health/`, les fichiers sont dans **`…/mobility-health/frontend-simple/`** (équivalent canonique avec espace : `'/var/www/Mobility_Health/Mobility Health/frontend-simple'`). |
| **Backend** | **`/var/www/Mobility_Health/Mobility_Health/`** | Uniquement ce dossier (double `Mobility_Health`, sans espace). |

---

## 3. Commandes SCP (à lancer depuis la racine du projet)

### Frontend → /var/www/mobility-health/

```powershell
scp -r -o StrictHostKeyChecking=no frontend-simple root@srv1324425.hstgr.cloud:/var/www/mobility-health/
```

Résultat : `/var/www/mobility-health/frontend-simple/` (HTML, CSS, JS).  
Si votre site sert les fichiers à la racine de `mobility-health` (sans sous-dossier), vous pouvez copier le **contenu** du frontend :
```powershell
scp -r -o StrictHostKeyChecking=no frontend-simple/* root@srv1324425.hstgr.cloud:/var/www/mobility-health/
```

---

### Backend → /var/www/Mobility_Health/Mobility_Health/

*(Utilisez ce chemin si `ls /var/www/Mobility_Health/Mobility_Health/` fonctionne. Sinon créez le dossier ou adaptez selon le résultat de `ls -la /var/www/`.)*

```powershell
scp -r -o StrictHostKeyChecking=no app root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/
scp -r -o StrictHostKeyChecking=no alembic root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/
scp -o StrictHostKeyChecking=no docker-compose.yml Dockerfile requirements.txt alembic.ini root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/
```

Avec `docker-compose.prod.yml` et `Dockerfile.prod` :
```powershell
scp -o StrictHostKeyChecking=no docker-compose.prod.yml Dockerfile.prod root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/
```

---

## 4. Si le backend est ailleurs

Si votre `docker-compose.yml` n’est pas sous `…/Mobility_Health/Mobility_Health/`, adaptez les commandes après `ls -la` / `find /var/www -name docker-compose.yml`.

**Ne pas** utiliser seul le dossier `backend` sous `mobility-health` s’il n’est pas celui qui pilote les conteneurs en production.

---

## 5. Après la copie (sur le serveur)

```bash
ssh root@srv1324425.hstgr.cloud
cd /var/www/Mobility_Health/Mobility_Health
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache api
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api
systemctl reload nginx
```
