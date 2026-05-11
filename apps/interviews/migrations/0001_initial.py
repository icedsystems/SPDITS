import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('assignments', '0001_initial'),
        ('participants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'), ('assigned', 'Assigned'), ('in_progress', 'In Progress'),
                        ('completed', 'Completed'), ('refused', 'Refused'),
                        ('unreachable', 'Unreachable'), ('callback_required', 'Callback Required'),
                    ],
                    default='pending', max_length=30,
                )),
                ('scheduled_date', models.DateField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('callback_date', models.DateField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('refusal_reason', models.TextField(blank=True)),
                ('interview_data', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignment', models.OneToOneField(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='interview', to='assignments.assignment',
                )),
                ('enumerator', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='interviews', to='accounts.customuser',
                )),
                ('participant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='interviews', to='participants.participant',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='InterviewStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('previous_status', models.CharField(blank=True, max_length=30)),
                ('new_status', models.CharField(max_length=30)),
                ('notes', models.TextField(blank=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.customuser',
                )),
                ('interview', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='status_history', to='interviews.interview',
                )),
            ],
            options={'ordering': ['-changed_at']},
        ),
    ]
