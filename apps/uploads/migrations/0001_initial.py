import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('batch_id', models.CharField(max_length=50, unique=True)),
                ('file', models.FileField(upload_to='uploads/%Y/%m/%d/')),
                ('original_filename', models.CharField(max_length=255)),
                ('file_size', models.BigIntegerField(default=0)),
                ('file_type', models.CharField(max_length=20)),
                ('status', models.CharField(
                    choices=[
                        ('uploaded', 'Uploaded'), ('processing', 'Processing'), ('processed', 'Processed'),
                        ('pending_approval', 'Pending Approval'), ('approved', 'Approved'),
                        ('rejected', 'Rejected'), ('failed', 'Failed'),
                    ],
                    default='uploaded', max_length=30,
                )),
                ('source', models.CharField(
                    choices=[('web', 'Web Upload'), ('sftp', 'SFTP')], default='web', max_length=20,
                )),
                ('total_records', models.IntegerField(default=0)),
                ('valid_records', models.IntegerField(default=0)),
                ('invalid_records', models.IntegerField(default=0)),
                ('duplicate_records', models.IntegerField(default=0)),
                ('processing_errors', models.JSONField(default=list)),
                ('validation_report', models.JSONField(default=dict)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_notes', models.TextField(blank=True)),
                ('checksum_md5', models.CharField(blank=True, max_length=32)),
                ('is_malware_scanned', models.BooleanField(default=False)),
                ('celery_task_id', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('partner', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='upload_batches', to='accounts.partner',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_batches', to=settings.AUTH_USER_MODEL,
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='upload_batches', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Upload Batch', 'verbose_name_plural': 'Upload Batches'},
        ),
    ]
