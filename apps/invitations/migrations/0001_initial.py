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
            name='Invitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('organization', models.CharField(blank=True, max_length=255)),
                ('role', models.CharField(max_length=50)),
                ('token', models.CharField(editable=False, max_length=128, unique=True)),
                ('token_hash', models.CharField(db_index=True, editable=False, max_length=128)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'), ('accepted', 'Accepted'),
                        ('expired', 'Expired'), ('revoked', 'Revoked'),
                    ],
                    default='pending', max_length=20,
                )),
                ('expiry_time', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='accepted_invitation', to=settings.AUTH_USER_MODEL,
                )),
                ('invited_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_invitations', to=settings.AUTH_USER_MODEL,
                )),
                ('partner', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invitations', to='accounts.partner',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
