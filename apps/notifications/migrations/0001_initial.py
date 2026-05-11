import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('notification_type', models.CharField(
                    max_length=50,
                    choices=[
                        ('invitation', 'Invitation'), ('upload_approved', 'Upload Approved'),
                        ('upload_rejected', 'Upload Rejected'), ('new_upload', 'New Upload'),
                        ('assignment', 'New Assignment'), ('suspicious_activity', 'Suspicious Activity'),
                        ('sftp_alert', 'SFTP Alert'), ('system', 'System'),
                    ],
                )),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, max_length=500)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
