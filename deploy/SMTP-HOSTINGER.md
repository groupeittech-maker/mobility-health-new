# SMTP Hostinger — mobility-healthcare.cloud

Configuration de l’envoi d’e-mails (codes d’inscription, vérification) via **noreply@mobility-healthcare.cloud**.

## Paramètres Hostinger

| Variable | Valeur |
|----------|--------|
| `SMTP_HOST` | `smtp.hostinger.com` |
| `SMTP_PORT` | `465` |
| `SMTP_SECURITY` | `ssl` |
| `SMTP_USER` | `noreply@mobility-healthcare.cloud` |
| `SMTP_FROM_EMAIL` | `noreply@mobility-healthcare.cloud` |
| `SMTP_FROM_NAME` | `Mobility HealthCare` |
| `ASSURANCE_EMAIL` | `noreply@mobility-healthcare.cloud` (ou `contact@…` si créée) |

Le mot de passe est celui défini dans **hPanel → Emails → noreply@… → Gérer**.

## Déploiement automatique (recommandé)

1. GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Nom : **`SMTP_PASSWORD`** — valeur : mot de passe de la boîte noreply
3. Lancer **Actions** → **Configure SMTP (VPS)** → **Run workflow**  
   *(via SSH depuis GitHub Actions — ne nécessite pas le runner self-hosted)*

Le déploiement complet applique aussi SMTP si `SMTP_PASSWORD` est défini (voir `.github/workflows/deploy.yml`).

## Configuration manuelle sur le VPS

```bash
ssh root@srv1324425.hstgr.cloud
cd /var/www/Mobility_Health/Mobility_Health
git pull   # ou copier le script depuis le repo
SMTP_PASSWORD='VOTRE_MOT_DE_PASSE' bash /chemin/vers/configure-smtp-env.sh
```

Le script met à jour `.env`, redémarre `api` / `celery_worker` et affiche le résultat du probe.

## Vérification

```bash
curl -s https://srv1324425.hstgr.cloud/api/v1/health/email | python3 -m json.tool
```

Attendu :

- `"from_email": "noreply@mobility-healthcare.cloud"`
- `"probe_ok": true`

Ensuite, tester une **inscription** avec une vraie adresse e-mail : le code doit arriver sans erreur 503.

## Dépannage

| Symptôme | Cause probable |
|----------|----------------|
| `Domain not found` | Ancien domaine `home2main.com` encore dans `.env` — relancer Configure SMTP |
| `Authentication failed` | Mauvais `SMTP_PASSWORD` ou boîte non créée dans Hostinger |
| `probe_ok: false` après deploy | Secret `SMTP_PASSWORD` absent dans GitHub Actions |
| Inscription 503 | E-mail non envoyé — voir logs API : `docker compose logs api --tail 50` |
