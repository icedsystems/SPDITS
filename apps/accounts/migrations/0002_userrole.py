import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[
                        ('system_admin', 'System Admin'),
                        ('implementing_partner', 'Implementing Partner'),
                        ('supervisor', 'Supervisor'),
                        ('enumerator', 'Enumerator'),
                        ('compliance_officer', 'Compliance Officer'),
                        ('tracer', 'Tracer'),
                    ],
                    max_length=50,
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='extra_role_assignments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Extra User Role',
                'verbose_name_plural': 'Extra User Roles',
                'unique_together': {('user', 'role')},
            },
        ),
    ]
