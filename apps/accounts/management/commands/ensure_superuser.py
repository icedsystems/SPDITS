"""
Creates an initial superuser from environment variables if none exists.
Called from Docker entrypoint.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create initial superuser if no admin user exists'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@iced.org')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123!')
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')

        if not User.objects.filter(role='system_admin').exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='System',
                last_name='Admin',
                role='system_admin',
                is_invitation_accepted=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f'Superuser created: {email} (password from DJANGO_SUPERUSER_PASSWORD env var)'
            ))
        else:
            self.stdout.write('Superuser already exists — skipping.')
