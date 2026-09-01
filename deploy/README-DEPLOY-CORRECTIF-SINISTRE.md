# Déployer le correctif « Sinistre à valider » (médecin référent)

Le correctif modifie uniquement **`app/api/v1/hospital_sinistres.py`** (l’alerte n’est plus marquée « résolue » à la création du séjour).

## Option 1 : Déploiement complet (quand SSH fonctionne)

Depuis la racine du projet :

```powershell
.\deploy.ps1
```

À adapter dans `deploy.ps1` si ton serveur est différent : `$SSH_HOST`, `$SSH_USER`, `$SERVER_BACKEND`.

## Option 2 : Déploiement du seul fichier modifié

1. Dans `deploy\deploy-fix-sinistre.ps1`, vérifier/corriger :
   - `$SSH_HOST` (ex. `82.112.242.86` ou `srv1324425.hstgr.cloud`)
   - `$SSH_USER` (ex. `deployer` ou `root`)
   - `$SERVER_BACKEND` (ex. `/var/www/mobility-health/backend`)

2. Lancer :

```powershell
.\deploy\deploy-fix-sinistre.ps1
```

3. En SSH sur le serveur, reconstruire et redémarrer l’API :

```bash
cd /var/www/mobility-health/backend
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build api
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api
```

## Option 3 : GitHub Actions (push sur `main`)

Si le dépôt est sur GitHub et que les secrets (`SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`) sont configurés :

1. Committer et pousser le correctif sur `main`.
2. Le workflow `.github/workflows/deploy.yml` se déclenche et déploie frontend + backend.

## Si SSH timeout (comme lors du premier essai)

- Vérifier que le serveur accepte les connexions SSH (port 22, firewall).
- Tester depuis ta machine : `ssh deployer@82.112.242.86` (ou l’hôte que tu utilises).
- Si tu déploies depuis un autre poste (VPN, autre réseau), utiliser le script ou Option 3 à partir de ce poste.
