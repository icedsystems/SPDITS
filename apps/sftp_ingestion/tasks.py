import os
import hashlib
import logging
import shutil
from datetime import datetime
from celery import shared_task

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ['.csv', '.xls', '.xlsx']


@shared_task(name='apps.sftp_ingestion.tasks.poll_sftp_folders')
def poll_sftp_folders():
    """Poll SFTP inbound directories for all active partners."""
    from .models import SFTPConfig
    configs = SFTPConfig.objects.filter(is_active=True).select_related('partner')
    for config in configs:
        try:
            _process_sftp_config(config)
        except Exception as e:
            logger.exception(f'Error polling SFTP for {config.partner.name}: {e}')


def _process_sftp_config(config):
    """Process one partner's SFTP inbound directory."""
    import paramiko
    from django.conf import settings

    sftp_host = settings.SFTP_HOST
    sftp_port = settings.SFTP_PORT

    transport = paramiko.Transport((sftp_host, sftp_port))
    try:
        transport.connect(username=config.username)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            files = sftp.listdir_attr(config.inbound_directory)
            for f_attr in files:
                if not any(f_attr.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    continue
                remote_path = f"{config.inbound_directory}/{f_attr.filename}"
                ingest_sftp_file.delay(config.partner.pk, remote_path, f_attr.filename, f_attr.st_size or 0)
        finally:
            sftp.close()
    finally:
        transport.close()


@shared_task(name='apps.sftp_ingestion.tasks.ingest_sftp_file', bind=True, max_retries=3)
def ingest_sftp_file(self, partner_pk, remote_path, filename, file_size):
    """Download and ingest a single SFTP file."""
    import paramiko
    from django.conf import settings
    from django.utils import timezone
    from apps.accounts.models import Partner
    from apps.uploads.models import UploadBatch, BatchStatus
    from apps.processing.tasks import process_upload_batch
    from .models import SFTPIngestionLog, SFTPConfig, SFTPIngestionStatus

    try:
        partner = Partner.objects.get(pk=partner_pk)
        sftp_config = partner.sftp_config
    except (Partner.DoesNotExist, SFTPConfig.DoesNotExist):
        logger.error(f'Partner or SFTP config not found for pk={partner_pk}')
        return

    log = SFTPIngestionLog.objects.create(
        partner=partner,
        filename=filename,
        remote_path=remote_path,
        file_size=file_size,
        status=SFTPIngestionStatus.PROCESSING,
    )

    try:
        sftp_host = settings.SFTP_HOST
        sftp_port = settings.SFTP_PORT
        transport = paramiko.Transport((sftp_host, sftp_port))
        transport.connect(username=sftp_config.username)
        sftp = paramiko.SFTPClient.from_transport(transport)

        local_dir = os.path.join(settings.MEDIA_ROOT, 'sftp_processing', str(partner_pk))
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        sftp.get(remote_path, local_path)

        # Compute MD5
        md5 = hashlib.md5(open(local_path, 'rb').read()).hexdigest()

        # Duplicate check
        if SFTPIngestionLog.objects.filter(partner=partner, checksum_md5=md5, status=SFTPIngestionStatus.COMPLETED).exists():
            log.status = SFTPIngestionStatus.DUPLICATE
            log.save(update_fields=['status'])
            os.remove(local_path)
            logger.info(f'Skipping duplicate SFTP file: {filename}')
            return

        log.local_path = local_path
        log.checksum_md5 = md5
        log.save(update_fields=['local_path', 'checksum_md5'])

        # Move to uploads/sftp directory
        sftp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'sftp',
                                        datetime.now().strftime('%Y/%m/%d'))
        os.makedirs(sftp_upload_dir, exist_ok=True)
        final_path = os.path.join(sftp_upload_dir, filename)
        shutil.move(local_path, final_path)

        # Create UploadBatch
        import uuid
        batch = UploadBatch(
            partner=partner,
            original_filename=filename,
            file_size=file_size,
            file_type=filename.rsplit('.', 1)[-1].upper() if '.' in filename else 'UNKNOWN',
            checksum_md5=md5,
            source='sftp',
            status=BatchStatus.UPLOADED,
        )
        rel_path = os.path.relpath(final_path, settings.MEDIA_ROOT)
        batch.file.name = rel_path
        batch.save()

        log.upload_batch = batch
        log.status = SFTPIngestionStatus.COMPLETED
        log.processed_at = timezone.now()
        log.save(update_fields=['upload_batch', 'status', 'processed_at'])

        task = process_upload_batch.delay(batch.pk)
        batch.celery_task_id = task.id
        batch.status = BatchStatus.PROCESSING
        batch.save(update_fields=['celery_task_id', 'status'])

        # Archive remote file
        if sftp_config.archive_directory:
            try:
                sftp.rename(remote_path, f"{sftp_config.archive_directory}/{filename}")
            except Exception:
                pass
        sftp.close()
        transport.close()
        logger.info(f'SFTP file ingested: {filename} for {partner.name}')

    except Exception as exc:
        logger.exception(f'SFTP ingestion error for {filename}: {exc}')
        log.status = SFTPIngestionStatus.FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        raise self.retry(exc=exc, countdown=120)
