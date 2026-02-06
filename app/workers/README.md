# Workers Celery - Mobility Health

Système de workers asynchrones pour gérer les notifications, rappels et tâches en arrière-plan.

## Configuration

### Variables d'environnement

Ajoutez ces variables dans votre fichier `.env` :

```env
# Redis (déjà configuré)
REDIS_URL=redis://localhost:6379/0

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe
SMTP_FROM_EMAIL=noreply@mobilityhealth.com
SMTP_FROM_NAME=Mobility Health

# SMS (Twilio - optionnel)
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=votre-account-sid
TWILIO_AUTH_TOKEN=votre-auth-token
TWILIO_FROM_NUMBER=+1234567890

# Push Notifications (FCM - optionnel)
FCM_SERVER_KEY=votre-fcm-server-key
FCM_PROJECT_ID=votre-project-id
```

## Démarrage des Workers

### 1. Worker Celery

Le worker traite les tâches en file d'attente.

**Linux/Mac:**
```bash
./scripts/start_celery_worker.sh
```

**Windows PowerShell:**
```powershell
.\scripts\start_celery_worker.ps1
```

**Manuellement:**
```bash
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=4
```

### 2. Celery Beat (Scheduler)

Celery Beat planifie les tâches périodiques.

**Linux/Mac:**
```bash
./scripts/start_celery_beat.sh
```

**Windows PowerShell:**
```powershell
.\scripts\start_celery_beat.ps1
```

**Manuellement:**
```bash
celery -A app.core.celery_app:celery_app beat --loglevel=info
```

## Queues

Les tâches sont réparties dans différentes queues :

- `default` : Tâches générales
- `notifications` : Envoi d'emails, SMS, push
- `reminders` : Rappels de questionnaires

## Tâches disponibles

### Notifications

- `send_email` : Envoyer un email
- `send_sms` : Envoyer un SMS
- `send_push` : Envoyer une notification push
- `send_notification_multi_channel` : Envoyer sur plusieurs canaux

### Rappels

- `schedule_questionnaire_reminder` : Planifier un rappel
- `send_questionnaire_reminder` : Envoyer un rappel

### Tâches périodiques

- `process_pending_notifications` : Traiter les notifications en attente (toutes les 5 min)
- `process_questionnaire_reminders` : Envoyer les rappels de questionnaires (tous les jours à 9h)
- `retry_failed_tasks` : Réessayer les tâches échouées (toutes les 10 min)

## Retry et Exponential Backoff

Toutes les tâches de notification ont un système de retry automatique :

- **Max retries** : 3 tentatives
- **Exponential backoff** : 60s, 120s, 240s
- **Automatic retry** : En cas d'échec temporaire

## Monitoring

### Voir les tâches en cours

```bash
celery -A app.core.celery_app:celery_app inspect active
```

### Voir les tâches planifiées

```bash
celery -A app.core.celery_app:celery_app inspect scheduled
```

### Voir les statistiques

```bash
celery -A app.core.celery_app:celery_app inspect stats
```

## Docker Compose

Pour démarrer les workers avec Docker, ajoutez ces services dans `docker-compose.yml` :

```yaml
celery_worker:
  build: .
  command: celery -A app.core.celery_app:celery_app worker --loglevel=info
  volumes:
    - .:/app
  depends_on:
    - redis
    - db

celery_beat:
  build: .
  command: celery -A app.core.celery_app:celery_app beat --loglevel=info
  volumes:
    - .:/app
  depends_on:
    - redis
    - db
```
