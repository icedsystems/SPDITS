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
            name='Participant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('pseudo_code', models.CharField(db_index=True, max_length=50, unique=True)),
                ('status', models.CharField(
                    choices=[
                        ('uploaded', 'Uploaded'), ('tracing', 'Tracing'), ('traced', 'Traced'),
                        ('assigned', 'Assigned'), ('interviewed', 'Interviewed'), ('closed', 'Closed'),
                    ],
                    default='uploaded', max_length=30,
                )),
                ('data', models.JSONField(default=dict)),
                ('row_number', models.IntegerField(default=0)),
                ('is_duplicate', models.BooleanField(default=False)),
                ('is_valid', models.BooleanField(default=True)),
                ('validation_errors', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('partner', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='participants', to='accounts.partner',
                )),
                ('upload_batch', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='participants', to='uploads.uploadbatch',
                )),
                ('duplicate_of', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='participants.participant',
                )),
            ],
            options={'ordering': ['pseudo_code'], 'verbose_name': 'Participant', 'verbose_name_plural': 'Participants'},
        ),
        migrations.CreateModel(
            name='IdentityMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('encrypted_name', models.BinaryField(blank=True, null=True)),
                ('encrypted_national_id', models.BinaryField(blank=True, null=True)),
                ('encrypted_passport', models.BinaryField(blank=True, null=True)),
                ('encrypted_phone', models.BinaryField(blank=True, null=True)),
                ('encrypted_alt_phone', models.BinaryField(blank=True, null=True)),
                ('encrypted_email', models.BinaryField(blank=True, null=True)),
                ('encrypted_address', models.BinaryField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('participant', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='identity_map', to='participants.participant',
                )),
            ],
        ),
        migrations.CreateModel(
            name='ReIdentificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('reason', models.TextField()),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('session_id', models.CharField(blank=True, max_length=40)),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
                ('fields_accessed', models.JSONField(default=list)),
                ('participant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reidentification_logs', to='participants.participant',
                )),
                ('requested_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, to='accounts.customuser',
                )),
            ],
            options={'ordering': ['-viewed_at']},
        ),
    ]
