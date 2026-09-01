# Déploiement sur le serveur

## Déploiement complet (frontend + backend)

À la racine du projet :

```powershell
.\deploy.ps1
```

Le script :
0. Crée sur le VPS les dossiers cibles s’ils n’existent pas
1. Déploie le frontend vers `$SERVER_FRONTEND` (défaut : `/var/www/mobility-health/frontend-simple`)
2. Déploie le backend vers `$SERVER_BACKEND` (défaut : `/var/www/Mobility_Health/Mobility_Health`)

Chemins documentés après vérification sur le VPS : **`deploy/SCP-DEPLOY-CHEMINS.md`**
3. Reconstruit l’image API (avec `docker-compose.prod.yml` si présent)
4. Démarre les services (db, redis, minio, api, celery)
5. Lance les migrations Alembic
6. Redémarre l’API et vérifie Nginx

## Configuration du serveur

Dans **`deploy.ps1`** (lignes 5–9), vérifier :

- **`$SSH_HOST`** : IP ou hostname du VPS (ex. `82.112.242.86` ou `srv1324425.hstgr.cloud`)
- **`$SSH_USER`** : utilisateur SSH (par défaut **`root`** dans `deploy.ps1` ; sinon `deployer`)
- **`$FILE_OWNER`** : propriétaire des fichiers après copie (ex. `root:root` ou `deployer:deployer`)
- **`$SERVER_FRONTEND`** / **`$SERVER_BACKEND`** : chemins sur le serveur (défaut aligné sur **`deploy/SCP-DEPLOY-CHEMINS.md`**).

Si la connexion SSH timeout : utiliser l’autre hôte (commenter/décommenter la ligne `$SSH_HOST`), vérifier le pare-feu (port 22), le VPN ou le réseau.

## Prérequis

- OpenSSH (Client) installé sur Windows
- Accès SSH au serveur (mot de passe ou clé)
- Sur le serveur : Docker, Docker Compose, `.env` configuré (voir `INSTALL_BD_VPS.md`). Les répertoires de déploiement sont créés par `deploy.ps1` ; en **SCP manuel**, voir **`deploy/SCP-COMMANDES-MANUEL.md`** (`mkdir` avant copie).

## Déploiement manuel (si le script échoue)

1. Copier le code (rsync, scp, ou Git sur le serveur).
2. En SSH sur le serveur :

```bash
cd /var/www/Mobility_Health/Mobility_Health
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache api
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api alembic upgrade head
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api
sudo systemctl reload nginx
```

## Vérification

- API : https://srv1324425.hstgr.cloud/health (ou l’URL de votre serveur)
- Frontend : même domaine, selon la config Nginx
