from django.apps import AppConfig


class SftpIngestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sftp_ingestion'
    verbose_name = 'SFTP Ingestion'
