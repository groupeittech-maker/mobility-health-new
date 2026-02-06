from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Configuration Celery avec Redis comme broker et backend
celery_app = Celery(
    "mobility_health",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Configuration Celery
celery_app.conf.update(
    # Sérialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_accept_content=["json"],
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Tracking
    task_track_started=True,
    task_send_sent_event=True,
    
    # Time limits
    task_time_limit=30 * 60,  # 30 minutes max par tâche
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_time_limit=1200,  # 20 minutes max pour un worker
    worker_max_tasks_per_child=1000,
    
    # Prefetch
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Queues Redis
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    
    # Résultats
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    result_expires=3600,  # Résultats expirés après 1 heure
    
    # Retry configuration globale
    task_autoretry_for=(Exception,),
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # Max 10 minutes
    task_retry_jitter=True,
    
    # Beat schedule pour les tâches périodiques
    beat_schedule={
        "send-pending-notifications": {
            "task": "app.workers.tasks.process_pending_notifications",
            "schedule": crontab(minute="*/5"),  # Toutes les 5 minutes
            "options": {"queue": "default"},
        },
        "send-questionnaire-reminders": {
            "task": "app.workers.tasks.process_questionnaire_reminders",
            "schedule": crontab(hour=9, minute=0),  # Tous les jours à 9h
            "options": {"queue": "reminders"},
        },
        "retry-failed-tasks": {
            "task": "app.workers.tasks.retry_failed_tasks",
            "schedule": crontab(minute="*/10"),  # Toutes les 10 minutes
            "options": {"queue": "default"},
        },
    },
)

# Configuration des routes par type de tâche (queues Redis)
celery_app.conf.task_routes = {
    # Notifications
    "app.workers.tasks.send_email": {"queue": "notifications"},
    "app.workers.tasks.send_sms": {"queue": "notifications"},
    "app.workers.tasks.send_push": {"queue": "notifications"},
    "app.workers.tasks.send_notification_multi_channel": {"queue": "notifications"},
    
    # Rappels
    "app.workers.tasks.send_questionnaire_reminder": {"queue": "reminders"},
    "app.workers.tasks.schedule_questionnaire_reminder": {"queue": "reminders"},
    "app.workers.tasks.process_questionnaire_reminders": {"queue": "reminders"},
    
    # Tâches périodiques
    "app.workers.tasks.process_pending_notifications": {"queue": "default"},
    "app.workers.tasks.retry_failed_tasks": {"queue": "default"},
}

# Configuration des priorités par queue
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5