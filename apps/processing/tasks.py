import logging
import hashlib
import pandas as pd
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)

DIRECT_IDENTIFIER_FIELDS = [
    'name', 'full_name', 'national_id', 'id_number', 'passport',
    'phone', 'phone_number', 'email', 'address', 'exact_address',
    'alt_phone', 'alternative_phone',
]

REQUIRED_FIELDS = ['name', 'gender', 'county']


@shared_task(name='apps.processing.tasks.process_upload_batch', bind=True, max_retries=3)
def process_upload_batch(self, batch_pk):
    """Main Celery task: read, validate, deduplicate an uploaded file."""
    from apps.uploads.models import UploadBatch, BatchStatus
    from apps.notifications.tasks import notify_admin_new_upload

    try:
        batch = UploadBatch.objects.get(pk=batch_pk)
    except UploadBatch.DoesNotExist:
        logger.error(f'UploadBatch {batch_pk} not found')
        return

    try:
        batch.status = BatchStatus.PROCESSING
        batch.save(update_fields=['status'])

        df = _read_file(batch.file.path)
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]

        errors = []
        valid_rows = []
        invalid_rows = []
        duplicates = []
        seen_hashes = set()

        for idx, row in df.iterrows():
            row_data = row.to_dict()
            row_errors = _validate_row(row_data, idx + 2)
            row_hash = _hash_row(row_data)
            if row_hash in seen_hashes:
                duplicates.append(idx)
                continue
            seen_hashes.add(row_hash)
            if row_errors:
                invalid_rows.append({'row': idx + 2, 'errors': row_errors, 'data': row_data})
                errors.extend(row_errors)
            else:
                valid_rows.append({'row': idx + 2, 'data': row_data, 'hash': row_hash})

        batch.total_records = len(df)
        batch.valid_records = len(valid_rows)
        batch.invalid_records = len(invalid_rows)
        batch.duplicate_records = len(duplicates)
        batch.processing_errors = errors[:100]
        batch.validation_report = {
            'columns': list(df.columns),
            'sample_invalid': invalid_rows[:5],
            'total_rows': len(df),
        }
        batch.status = BatchStatus.PENDING_APPROVAL
        batch.save()

        # Cache valid row data for participant creation on approval
        import json
        from django.core.cache import cache
        cache.set(f'batch_valid_rows_{batch_pk}', json.dumps(valid_rows), timeout=86400)

        notify_admin_new_upload.delay(batch_pk)
        logger.info(f'Batch {batch.batch_id} processed: {len(valid_rows)} valid, {len(invalid_rows)} invalid')

    except Exception as exc:
        logger.exception(f'Error processing batch {batch_pk}: {exc}')
        batch.status = BatchStatus.FAILED
        batch.processing_errors = [str(exc)]
        batch.save(update_fields=['status', 'processing_errors'])
        raise self.retry(exc=exc, countdown=60)


def _read_file(path: str) -> pd.DataFrame:
    if path.endswith('.csv'):
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    elif path.endswith('.xlsx'):
        return pd.read_excel(path, dtype=str, keep_default_na=False)
    elif path.endswith('.xls'):
        return pd.read_excel(path, dtype=str, keep_default_na=False, engine='xlrd')
    raise ValueError(f'Unsupported file type: {path}')


def _validate_row(row: dict, row_num: int) -> list:
    errors = []
    for field in REQUIRED_FIELDS:
        if not row.get(field, '').strip():
            errors.append(f'Row {row_num}: Missing required field "{field}"')
    return errors


def _hash_row(row: dict) -> str:
    stable_keys = sorted(k for k in row if row[k])
    value = '|'.join(f'{k}:{row[k]}' for k in stable_keys)
    return hashlib.sha256(value.encode()).hexdigest()


@shared_task(name='apps.processing.tasks.pseudocode_batch_participants')
def pseudocode_batch_participants(batch_pk):
    """Create Participant records and IdentityMap after admin approval."""
    import json
    from django.core.cache import cache
    from apps.uploads.models import UploadBatch
    from apps.participants.models import Participant, IdentityMap, ParticipantStatus
    from apps.participants.utils import generate_pseudocode

    try:
        batch = UploadBatch.objects.get(pk=batch_pk)
    except UploadBatch.DoesNotExist:
        return

    cached = cache.get(f'batch_valid_rows_{batch_pk}')
    if not cached:
        logger.warning(f'No cached rows for batch {batch_pk}, re-reading file')
        df = _read_file(batch.file.path)
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
        valid_rows = [{'row': i + 2, 'data': row.to_dict()} for i, row in df.iterrows()]
    else:
        valid_rows = json.loads(cached)

    created = 0
    with transaction.atomic():
        for item in valid_rows:
            data = item['data']
            pseudo = generate_pseudocode()
            safe_data = {k: v for k, v in data.items() if k not in DIRECT_IDENTIFIER_FIELDS}
            p = Participant.objects.create(
                pseudo_code=pseudo,
                partner=batch.partner,
                upload_batch=batch,
                status=ParticipantStatus.UPLOADED,
                data=safe_data,
                row_number=item.get('row', 0),
            )
            identity = IdentityMap(participant=p)
            identity.set_identifiers(data)
            identity.save()
            created += 1

    logger.info(f'Created {created} participants for batch {batch.batch_id}')
    cache.delete(f'batch_valid_rows_{batch_pk}')
    return created
