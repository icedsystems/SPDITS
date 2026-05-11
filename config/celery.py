import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('spdits')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_routes = {
    'apps.uploads.tasks.*': {'queue': 'uploads'},
    'apps.sftp_ingestion.tasks.*': {'queue': 'sftp'},
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.processing.tasks.*': {'queue': 'uploads'},
}

app.conf.beat_schedule = {
    'sftp-poll-every-minute': {
        'task': 'apps.sftp_ingestion.tasks.poll_sftp_folders',
        'schedule': 60.0,
    },
    'cleanup-expired-invitations': {
        'task': 'apps.invitations.tasks.cleanup_expired_invitations',
        'schedule': 3600.0,
    },
}
