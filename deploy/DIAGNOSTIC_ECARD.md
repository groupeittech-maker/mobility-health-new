# Diagnostic e-carte (affichage ne fonctionne pas)

## 1. Vérifier que le conteneur reçoit bien la variable

Sur le serveur :

```bash
docker exec mobility_health_api env | grep -E "API_PUBLIC|MINIO"
```

Vous devez voir par exemple :
- `MINIO_ENDPOINT=minio:9000`
- `API_PUBLIC_BASE_URL=https://srv1324425.hstgr.cloud`

Si **API_PUBLIC_BASE_URL** n’apparaît pas, le conteneur n’a pas été recréé avec la bonne config.

---

## 2. Recréer le conteneur API (important)

Un simple `docker compose restart api` ne recharge pas les variables d’environnement. Il faut recréer le conteneur :

```bash
cd /var/www/Mobility_Health/Mobility_Health
docker compose up -d api
```

Cela recrée le conteneur avec les variables du fichier `.env`.

---

## 3. Vérifier la config côté API

Depuis votre PC ou le serveur :

```bash
curl -s https://srv1324425.hstgr.cloud/api/v1/debug/ecard-config
```

Ou en local sur le serveur :

```bash
curl -s http://127.0.0.1:8000/api/v1/debug/ecard-config
```

Réponse attendue si tout est bon :
```json
{
  "use_ecard_proxy": true,
  "API_PUBLIC_BASE_URL": "https://srv1324425.hstgr.cloud",
  "MINIO_ENDPOINT": "minio:9000",
  "message": "URL proxy utilisée pour l'e-carte"
}
```

Si `use_ecard_proxy` est `false`, vérifier le `.env` et refaire l’étape 2.

---

## 4. Déployer les fichiers modifiés (SCP)

Depuis votre PC (dossier du projet) :

```powershell
scp app/api/v1/__init__.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/api/v1/
scp app/api/v1/subscriptions.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/api/v1/
scp app/core/config.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/core/
scp app/core/security.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/core/
scp app/api/v1/attestations.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/api/v1/
scp app/api/v1/auth.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/api/v1/
scp app/services/attestation_service.py root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/app/services/
scp docker-compose.yml root@srv1324425.hstgr.cloud:/var/www/Mobility_Health/Mobility_Health/
```

Puis sur le serveur : `docker compose up -d api`

---

## 5. Tester l’URL de l’e-carte dans le navigateur

Une fois qu’une attestation avec e-carte existe, l’API doit renvoyer une URL du type :

`https://srv1324425.hstgr.cloud/api/v1/attestations/5/ecard/download?token=...`

Ouvrez cette URL dans un nouvel onglet (en étant connecté ou avec le token) : l’image doit s’afficher. Si vous avez une 404 ou une erreur, le problème vient du chemin ou du proxy Nginx.
