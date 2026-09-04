# Chaîne CI/CD automatisée — Mobility Health

Objectif : **vous ne gérez que le code** ; le reste (tests, merge, déploiement) est automatique.

## Flux automatique

```mermaid
flowchart TD
    A[Vous poussez une branche / PR] --> B[CI Pipeline]
    B -->|❌ échec| C[Corriger et repousser]
    C --> A
    B -->|✅ PR| D[Auto Merge → main]
    B -->|✅ push main| E[Deploy VPS]
    D --> F[CI sur main]
    F -->|✅| E
    F -->|❌| C
    E -->|❌ health check| C
    E -->|✅| G[Sync local : scripts/sync-local-from-main]
```

| Étape | Déclencheur | Workflow | Action |
|-------|-------------|----------|--------|
| 1 | Push branche | — | Vous codez et poussez |
| 2 | PR ouverte | `ci.yml` | Tests backend, frontend, Flutter, Docker |
| 3 | CI vert sur PR | `auto-merge.yml` | Fusion automatique dans `main` |
| 4 | Push sur `main` | `ci.yml` | Re-validation sur main |
| 5 | CI vert sur main | `deploy.yml` | Déploiement VPS + health check |
| 6 | Deploy OK | — | `./scripts/sync-local-from-main.sh` sur votre machine |

## Configuration unique (GitHub)

### 1. Secrets (Settings → Secrets → Actions)

| Secret | Description |
|--------|-------------|
| `SSH_HOST` | Hostname VPS (ex. `srv1324425.hstgr.cloud`) — **pas** une ancienne IP figée |
| `SSH_USER` | Utilisateur SSH (ex. `root` ou `deployer`) |
| `SSH_PRIVATE_KEY` | Clé privée SSH (contenu du fichier, pas le `.pub`) |
| `SSH_PORT` | *(optionnel)* Port SSH si différent de 22 |

### 2. Protection de la branche `main` (Settings → Branches)

- ✅ Require status checks before merging
- Checks requis :
  - `CI Gate`
  - `Backend (pytest + lint)`
  - `Frontend (charte + assets)`
  - `Flutter (analyze + test + build)`
  - `Docker build API`
- ❌ **Ne pas** exiger de review humaine si vous voulez 100 % auto
- ✅ Allow auto-merge (Settings → General → Pull Requests)

### 3. Désactiver le merge auto sur une PR

Ajoutez le label **`no-auto-merge`** sur la PR concernée.

## Workflows

| Fichier | Rôle |
|---------|------|
| `.github/workflows/ci.yml` | Tests sur PR et push `main` / `develop` |
| `.github/workflows/auto-merge.yml` | Fusion PR → `main` si CI vert |
| `.github/workflows/deploy.yml` | Déploiement VPS après CI vert sur `main` |

Le déploiement **ne se lance plus** directement au push : il attend le succès du CI sur `main`.

Déploiement manuel d'urgence : Actions → **Deploy to Hostinger VPS** → Run workflow.

## Mise à jour locale (étape 5)

Après un déploiement réussi (notification GitHub ou e-mail Actions) :

**Linux / macOS :**
```bash
./scripts/sync-local-from-main.sh
```

**Windows (PowerShell) :**
```powershell
.\scripts\sync-local-from-main.ps1
```

> GitHub ne peut pas modifier votre PC automatiquement : cette commande est le seul geste local (quelques secondes).

## En cas d'échec

| Échec | Que faire |
|-------|-----------|
| CI rouge sur PR | Corriger le code, repousser → CI relance → merge auto si OK |
| CI rouge sur main | Corriger, PR ou push direct → redeploy après CI vert |
| Deploy rouge | Voir logs Actions + `docker compose logs api` sur le VPS |
| Health check API | Vérifier https://srv1324425.hstgr.cloud/health |
| `Network is unreachable` (SSH) | Voir § [Deploy SSH](#deploy-ssh--problèmes-de-connexion) ci-dessous |
| `Connection timed out` port 22 | Firewall Hostinger bloque le runner GitHub — voir § Deploy SSH |

## Deploy SSH — problèmes de connexion

### `Connection timed out` (port 22)

Symptôme dans Actions :

```text
ssh: connect to host *** port 22: Connection timed out
```

**Diagnostic (logs du job)** : l’étape « Vérifier secrets et réseau » affiche l’IP du runner GitHub et indique si le port TCP est joignable.

**Cause la plus fréquente** : le **firewall Hostinger** (hPanel) n’autorise pas toutes les IP des runners GitHub Actions (~7000 plages). Le déploiement peut réussir puis échouer au run suivant (IP runner différente).

**Correctifs (sur le VPS / hPanel)** :

1. **hPanel → VPS → Security → Firewall** : règle **TCP 22** depuis **Anywhere** (`0.0.0.0/0`). L’accès reste protégé par clé SSH (`authorized_keys`), pas par mot de passe.
2. Sur le VPS (SSH depuis votre PC) :
   ```bash
   bash deploy/fix-github-actions-ssh-firewall.sh
   ```
3. Vérifier **fail2ban** si des IP GitHub ont été bannies :
   ```bash
   fail2ban-client status sshd
   ```
4. Secret **`SSH_HOST`** = hostname `srv1324425.hstgr.cloud` (résout l’IP actuelle `76.13.36.246`), **pas** l’ancienne IP `82.112.242.86`.

**Relancer le déploiement** : Actions → **Deploy to Hostinger VPS** → Run workflow (le workflow réessaie 5× avec pause 15 s).

### `Network is unreachable`

Si le job **Test SSH connection** échoue avec `ssh: connect to host … port 22: Network is unreachable` :

1. **Secrets GitHub** (Settings → Secrets → Actions) :
   - `SSH_HOST` = hostname **ou IP publique** seule (`srv1324425.hstgr.cloud` ou `82.112.242.86`) — **sans** `user@`
   - `SSH_USER` = `root` ou `deployer`
   - `SSH_PRIVATE_KEY` = clé privée complète (`-----BEGIN OPENSSH PRIVATE KEY-----`)

2. **VPS Hostinger** : panneau → VPS → démarré, SSH activé (port 22).

3. **Firewall** : autoriser le port **22/TCP** depuis Internet (ou plages IP [GitHub Actions](https://api.github.com/meta) → champ `actions`).

4. **Clé publique** sur le VPS (`~/.ssh/authorized_keys`) — voir `apps/mhc/deploy-keys/README.md`.

5. **Test local** depuis votre PC :
   ```bash
   ssh -4 root@srv1324425.hstgr.cloud hostname
   ```
   Si local OK mais GitHub Actions KO → firewall bloque les runners (étape 3).

6. Le workflow force **IPv4** (`-4`, `AddressFamily inet`) pour éviter les échecs IPv6 des runners.

Déploiement manuel de secours : `.\deploy.ps1` ou Actions → **Deploy to Hostinger VPS** → Run workflow.

## Ce qui n'est pas automatisé

- **App mobile Flutter** : build Play Store / App Store (hors scope deploy VPS)
- **Secrets production** sur le VPS (`.env`) : configuration manuelle initiale
- **Sync locale** : une commande à lancer après deploy (voir ci-dessus)
