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
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('user_email', models.EmailField(blank=True)),
                ('user_role', models.CharField(blank=True, max_length=50)),
                ('action', models.CharField(db_index=True, max_length=100)),
                ('module', models.CharField(blank=True, db_index=True, max_length=100)),
                ('record_id', models.BigIntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('old_values', models.JSONField(blank=True, null=True)),
                ('new_values', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('session_id', models.CharField(blank=True, max_length=40)),
                ('extra_data', models.JSONField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Audit Log', 'verbose_name_plural': 'Audit Logs',
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['action', 'timestamp'], name='audit_action_ts_idx'),
                    models.Index(fields=['module', 'record_id'], name='audit_module_rec_idx'),
                    models.Index(fields=['user', 'timestamp'], name='audit_user_ts_idx'),
                ],
            },
        ),
    ]
