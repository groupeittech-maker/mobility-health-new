# Déploiement VPS — runner self-hosted (contourne firewall SSH Hostinger)

Quand GitHub Actions affiche **Port 22 injoignable**, le firewall Hostinger bloque les runners cloud.  
Solution recommandée : **runner self-hosted** installé sur le VPS (connexion sortante vers GitHub, pas de SSH entrant).

## Installation (une fois, ~5 min)

### 1. Connexion au VPS depuis votre PC

```bash
ssh root@srv1324425.hstgr.cloud
```

### 2. Token GitHub

GitHub → **groupeittech-maker/mobility-health-new** → **Settings** → **Actions** → **Runners** → **New self-hosted runner** → **Linux** → copier le token.

### 3. Installer le runner sur le VPS

```bash
git clone https://github.com/groupeittech-maker/mobility-health-new.git /tmp/mhc-setup
cd /tmp/mhc-setup
RUNNER_TOKEN="VOTRE_TOKEN" bash deploy/install-github-runner.sh
```

L’utilisateur `deployer` doit pouvoir exécuter `sudo` pour le déploiement Docker (ou adapter `RUNNER_USER=root`).

### 4. Activer le mode self-hosted dans GitHub

**Settings** → **Secrets and variables** → **Actions** → **Variables** → **New repository variable**

| Nom | Valeur |
|-----|--------|
| `USE_SELF_HOSTED_DEPLOY` | `true` |

### 5. Relancer le déploiement

**Actions** → **Deploy to Hostinger VPS** → **Run workflow**

Le job s’exécute **sur le VPS** (labels `self-hosted`, `mhc-vps`) — plus de SSH depuis `20.x.x.x`.

## Alternative : ouvrir le port 22 (firewall)

hPanel → **VPS** → **Security** → **Firewall** → règle **TCP 22** → source **Anywhere**.

Puis laisser `USE_SELF_HOSTED_DEPLOY` non défini ou `false` (mode SSH classique).

## Vérification

```bash
# Sur le VPS
systemctl status actions.runner.*  # runner actif
curl -sf https://srv1324425.hstgr.cloud/health
```

GitHub → **Settings** → **Actions** → **Runners** : runner **Idle** (vert).
