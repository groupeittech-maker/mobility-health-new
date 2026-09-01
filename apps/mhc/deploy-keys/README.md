# Clés SSH — déploiement GitHub Actions → VPS

Ce dossier stocke **localement** la paire de clés pour le workflow `.github/workflows/deploy.yml`.

**Les fichiers de clés ne sont jamais commités** (voir `.gitignore`).

## Générer la clé (étape 1)

### Windows (PowerShell)

```powershell
cd apps/mhc
.\scripts\generate-github-actions-ssh-key.ps1
```

### Linux / macOS / Cloud Agent

```bash
cd apps/mhc
chmod +x scripts/generate-github-actions-ssh-key.sh
./scripts/generate-github-actions-ssh-key.sh
```

## Fichiers créés

| Fichier | Usage |
|---|---|
| `deploy-keys/github_actions_mhc` | Clé **privée** → secret GitHub `SSH_PRIVATE_KEY` |
| `deploy-keys/github_actions_mhc.pub` | Clé **publique** → à copier sur le VPS |

## Étape 2 — VPS

```bash
ssh root@srv1324425.hstgr.cloud
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys   # coller le contenu de github_actions_mhc.pub
chmod 600 ~/.ssh/authorized_keys
```

## Étape 3 — Secrets GitHub

Repository → **Settings → Secrets and variables → Actions** :

| Secret | Valeur |
|---|---|
| `SSH_HOST` | `srv1324425.hstgr.cloud` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | contenu **complet** de `deploy-keys/github_actions_mhc` (fichier **sans** `.pub`) |

Sous Windows, copier ainsi :

```powershell
Get-Content -Raw ".\apps\mhc\deploy-keys\github_actions_mhc" | Set-Clipboard
```

Le secret doit commencer par `-----BEGIN OPENSSH PRIVATE KEY-----` et **pas** par `ssh-ed25519`.

## Test

```powershell
ssh -i apps/mhc/deploy-keys/github_actions_mhc root@srv1324425.hstgr.cloud hostname
```

Puis push sur `main` ou lancer **Deploy to Hostinger VPS** dans GitHub Actions.
