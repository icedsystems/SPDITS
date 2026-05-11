import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('uploads', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SFTPConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=100)),
                ('inbound_directory', models.CharField(max_length=500)),
                ('processing_directory', models.CharField(blank=True, max_length=500)),
                ('archive_directory', models.CharField(blank=True, max_length=500)),
                ('failed_directory', models.CharField(blank=True, max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('partner', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sftp_config', to='accounts.partner',
                )),
            ],
        ),
        migrations.CreateModel(
            name='SFTPIngestionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('filename', models.CharField(max_length=255)),
                ('remote_path', models.CharField(max_length=500)),
                ('local_path', models.CharField(blank=True, max_length=500)),
                ('file_size', models.BigIntegerField(default=0)),
                ('checksum_md5', models.CharField(blank=True, max_length=32)),
                ('status', models.CharField(
                    choices=[
                        ('detected', 'Detected'), ('processing', 'Processing'), ('completed', 'Completed'),
                        ('failed', 'Failed'), ('duplicate', 'Duplicate (Skipped)'),
                    ],
                    default='detected', max_length=20,
                )),
                ('error_message', models.TextField(blank=True)),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('partner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sftp_logs', to='accounts.partner',
                )),
                ('upload_batch', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to='uploads.uploadbatch',
                )),
            ],
            options={'ordering': ['-detected_at']},
        ),
    ]
