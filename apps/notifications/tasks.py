import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(name='apps.notifications.tasks.send_invitation_email')
def send_invitation_email(invitation_pk):
    from apps.invitations.models import Invitation
    try:
        inv = Invitation.objects.select_related('invited_by', 'partner').get(pk=invitation_pk)
        context = {
            'invitation': inv,
            'accept_url': inv.get_accept_url,
            'expiry_minutes': settings.INVITATION_EXPIRY_MINUTES,
        }
        body = render_to_string('emails/invitation.txt', context)
        html = render_to_string('emails/invitation.html', context)
        send_mail(
            subject=f'[ICED SPDITS] You have been invited',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[inv.email],
            html_message=html,
            fail_silently=False,
        )
        logger.info(f'Invitation email sent to {inv.email}')
    except Exception as e:
        logger.exception(f'Failed to send invitation email for pk={invitation_pk}: {e}')


@shared_task(name='apps.notifications.tasks.notify_admin_new_upload')
def notify_admin_new_upload(batch_pk):
    from apps.uploads.models import UploadBatch
    from apps.accounts.models import CustomUser, Role
    from .models import Notification, NotificationType
    from django.core.mail import EmailMultiAlternatives
    try:
        batch = UploadBatch.objects.select_related('partner', 'uploaded_by').get(pk=batch_pk)
        admins = CustomUser.objects.filter(role=Role.SYSTEM_ADMIN, is_active=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notification_type=NotificationType.NEW_UPLOAD,
                title='New upload pending approval',
                message=(f'{batch.partner.name} uploaded {batch.original_filename}. '
                         f'{batch.total_records} records, {batch.valid_records} valid.'),
                link=f'/uploads/{batch.pk}/',
            )
        context = {'batch': batch, 'app_url': settings.APP_URL}
        body = render_to_string('emails/upload_notification.txt', context)
        html = render_to_string('emails/upload_notification.html', context)
        admin_emails = list(admins.values_list('email', flat=True))
        if admin_emails:
            msg = EmailMultiAlternatives(
                subject=f'[SPDITS] New upload requires approval — {batch.partner.name}',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails,
            )
            msg.attach_alternative(html, 'text/html')
            msg.send(fail_silently=True)
            logger.info(f'Admin upload notification sent to {admin_emails} for batch {batch.batch_id}')
    except Exception as e:
        logger.exception(f'Failed to notify admin for batch {batch_pk}: {e}')


@shared_task(name='apps.notifications.tasks.notify_upload_decision')
def notify_upload_decision(batch_pk):
    from apps.uploads.models import UploadBatch, BatchStatus
    from .models import Notification, NotificationType
    from django.core.mail import EmailMultiAlternatives
    try:
        batch = UploadBatch.objects.select_related('partner', 'uploaded_by', 'reviewed_by').get(pk=batch_pk)
        if not batch.uploaded_by:
            return
        approved = batch.status == BatchStatus.APPROVED
        Notification.objects.create(
            recipient=batch.uploaded_by,
            notification_type=NotificationType.UPLOAD_APPROVED if approved else NotificationType.UPLOAD_REJECTED,
            title=f'Upload {"approved" if approved else "rejected"}',
            message=(f'Your upload {batch.original_filename} has been '
                     f'{"approved" if approved else "rejected"}.'
                     + (f' Notes: {batch.review_notes}' if batch.review_notes else '')),
            link=f'/uploads/{batch.pk}/',
        )
        context = {'batch': batch, 'approved': approved, 'app_url': settings.APP_URL}
        body = render_to_string('emails/upload_decision.txt', context)
        html = render_to_string('emails/upload_decision.html', context)
        msg = EmailMultiAlternatives(
            subject=f'[SPDITS] Upload {"Approved" if approved else "Rejected"} — {batch.original_filename}',
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[batch.uploaded_by.email],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
        logger.info(f'Upload decision email sent to {batch.uploaded_by.email} for batch {batch.batch_id}')
    except Exception as e:
        logger.exception(f'Failed to notify upload decision for batch {batch_pk}: {e}')
