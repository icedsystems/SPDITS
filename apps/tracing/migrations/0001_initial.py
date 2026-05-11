import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('participants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TracingLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('previous_status', models.CharField(blank=True, max_length=30)),
                ('new_status', models.CharField(max_length=30)),
                ('notes', models.TextField(blank=True)),
                ('contact_attempted', models.BooleanField(default=False)),
                ('contact_method', models.CharField(
                    blank=True, max_length=50,
                    choices=[('phone', 'Phone'), ('visit', 'Physical Visit'), ('sms', 'SMS'), ('email', 'Email'), ('other', 'Other')],
                )),
                ('location_found', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('participant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tracing_logs', to='participants.participant',
                )),
                ('updated_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tracing_updates', to='accounts.customuser',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
