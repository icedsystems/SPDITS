from django.apps import AppConfig


class TracingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tracing'
    verbose_name = 'Tracing'
