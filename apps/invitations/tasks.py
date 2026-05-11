from celery import shared_task
from django.utils import timezone
from .models import Invitation, InvitationStatus


@shared_task(name='apps.invitations.tasks.cleanup_expired_invitations')
def cleanup_expired_invitations():
    """Mark expired invitations."""
    count = Invitation.objects.filter(
        status=InvitationStatus.PENDING,
        expiry_time__lt=timezone.now()
    ).update(status=InvitationStatus.EXPIRED)
    return f'Marked {count} invitations as expired'
