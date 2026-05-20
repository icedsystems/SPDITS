"""
Management command: reset_for_testing

Wipes all application data from the database so a fresh test can be run.
The only user kept is pomboi@iced-eval.org (the system admin).
All other users, partners, participants, uploads, tracing, assignments,
interviews, audit logs, notifications, invitations and SFTP logs are deleted.

Usage:
    python manage.py reset_for_testing
    python manage.py reset_for_testing --confirm   # skip the interactive prompt
"""

from django.core.management.base import BaseCommand
from django.db import transaction


KEEP_EMAIL = 'pomboi@iced-eval.org'


class Command(BaseCommand):
    help = 'Reset all application data for a fresh test, keeping only the main admin account.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip the interactive confirmation prompt.',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                f'\nThis will DELETE all data except the account for {KEEP_EMAIL}.\n'
                'Type "yes" to continue, anything else to abort: '
            ), ending='')
            answer = input().strip().lower()
            if answer != 'yes':
                self.stdout.write(self.style.ERROR('Aborted — no changes made.'))
                return

        with transaction.atomic():
            self._clear_all()

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Database reset. Only {KEEP_EMAIL} remains.'
        ))

    def _clear_all(self):
        deleted_counts = {}

        # ── Participants & identity maps ────────────────────────────────────
        try:
            from apps.participants.models import IdentityMap, Participant
            n, _ = IdentityMap.objects.all().delete()
            deleted_counts['IdentityMap'] = n
            n, _ = Participant.objects.all().delete()
            deleted_counts['Participant'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  participants: {e}'))

        # ── Tracing ─────────────────────────────────────────────────────────
        try:
            from apps.tracing.models import TracingLog, TracingQueue
            n, _ = TracingLog.objects.all().delete()
            deleted_counts['TracingLog'] = n
            n, _ = TracingQueue.objects.all().delete()
            deleted_counts['TracingQueue'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  tracing: {e}'))

        # ── Assignments ──────────────────────────────────────────────────────
        try:
            from apps.assignments.models import Assignment
            n, _ = Assignment.objects.all().delete()
            deleted_counts['Assignment'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  assignments: {e}'))

        # ── Interviews ───────────────────────────────────────────────────────
        try:
            from apps.interviews.models import Interview
            n, _ = Interview.objects.all().delete()
            deleted_counts['Interview'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  interviews: {e}'))

        # ── Uploads / processing ─────────────────────────────────────────────
        try:
            from apps.uploads.models import UploadBatch
            n, _ = UploadBatch.objects.all().delete()
            deleted_counts['UploadBatch'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  uploads: {e}'))

        # ── SFTP ingestion logs ───────────────────────────────────────────────
        try:
            from apps.sftp_ingestion.models import SFTPIngestionLog
            n, _ = SFTPIngestionLog.objects.all().delete()
            deleted_counts['SFTPIngestionLog'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  sftp_ingestion: {e}'))

        # ── Audit logs ────────────────────────────────────────────────────────
        try:
            from apps.audit.models import AuditLog
            n, _ = AuditLog.objects.all().delete()
            deleted_counts['AuditLog'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  audit: {e}'))

        # ── Notifications ─────────────────────────────────────────────────────
        try:
            from apps.notifications.models import Notification
            n, _ = Notification.objects.all().delete()
            deleted_counts['Notification'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  notifications: {e}'))

        # ── Invitations ───────────────────────────────────────────────────────
        try:
            from apps.invitations.models import Invitation
            n, _ = Invitation.objects.all().delete()
            deleted_counts['Invitation'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  invitations: {e}'))

        # ── Celery beat / results (if present) ────────────────────────────────
        try:
            from django_celery_results.models import TaskResult
            n, _ = TaskResult.objects.all().delete()
            deleted_counts['TaskResult'] = n
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  celery results: {e}'))

        # ── Users — delete all except the keeper ─────────────────────────────
        from apps.accounts.models import CustomUser, UserRole, UserSession
        other_users = CustomUser.objects.exclude(email=KEEP_EMAIL)
        n_roles, _ = UserRole.objects.filter(user__in=other_users).delete()
        deleted_counts['UserRole'] = n_roles
        n_sessions, _ = UserSession.objects.filter(user__in=other_users).delete()
        deleted_counts['UserSession'] = n_sessions
        n_users, _ = other_users.delete()
        deleted_counts['CustomUser'] = n_users

        # Also clear sessions for the kept user so they get a clean login
        UserSession.objects.filter(user__email=KEEP_EMAIL).delete()

        # Make sure the kept admin has no force_password_change flag set
        try:
            admin = CustomUser.objects.get(email=KEEP_EMAIL)
            admin.force_password_change = False
            admin.save(update_fields=['force_password_change'])
            self.stdout.write(f'  Kept admin: {admin.get_full_name()} <{admin.email}>')
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'  WARNING: {KEEP_EMAIL} not found — no admin account remains!'
            ))

        # ── Partners ─────────────────────────────────────────────────────────
        from apps.accounts.models import Partner
        n, _ = Partner.objects.all().delete()
        deleted_counts['Partner'] = n

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('\n  Records deleted:')
        for model, count in deleted_counts.items():
            if count:
                self.stdout.write(f'    {model}: {count}')
