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
            name='Assignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('reassigned', 'Reassigned'), ('completed', 'Completed')],
                    default='active', max_length=20,
                )),
                ('notes', models.TextField(blank=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('enumerator', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    limit_choices_to={'role': 'enumerator'},
                    related_name='assignments', to='accounts.customuser',
                )),
                ('participant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments', to='participants.participant',
                )),
                ('supervisor', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    limit_choices_to={'role': 'supervisor'},
                    related_name='supervised_assignments', to='accounts.customuser',
                )),
            ],
            options={'ordering': ['-assigned_at']},
        ),
        migrations.AlterUniqueTogether(
            name='assignment',
            unique_together={('participant', 'enumerator', 'status')},
        ),
    ]
