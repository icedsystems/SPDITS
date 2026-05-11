import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def log_action(
    request,
    action: str,
    module: str = '',
    record_id: Optional[int] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    description: str = '',
    extra_data: Optional[dict] = None,
):
    """Create an immutable audit log entry."""
    from .models import AuditLog
    try:
        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None
        ip = ''
        if request:
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if ',' in ip:
                ip = ip.split(',')[0].strip()
        AuditLog.objects.create(
            user=user,
            user_email=user.email if user else '',
            user_role=user.role if user else '',
            action=action,
            module=module,
            record_id=record_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip or None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            session_id=request.session.session_key or '' if request and hasattr(request, 'session') else '',
            extra_data=extra_data,
        )
    except Exception as e:
        logger.exception(f'Failed to create audit log: {e}')


def log_action_celery(
    user_id: Optional[int],
    action: str,
    module: str = '',
    record_id: Optional[int] = None,
    description: str = '',
    extra_data: Optional[dict] = None,
):
    """Create audit log entry from Celery task (no request object)."""
    from .models import AuditLog
    from apps.accounts.models import CustomUser
    try:
        user = None
        user_email = ''
        user_role = ''
        if user_id:
            try:
                user = CustomUser.objects.get(pk=user_id)
                user_email = user.email
                user_role = user.role
            except CustomUser.DoesNotExist:
                pass
        AuditLog.objects.create(
            user=user,
            user_email=user_email,
            user_role=user_role,
            action=action,
            module=module,
            record_id=record_id,
            description=description,
            extra_data=extra_data,
        )
    except Exception as e:
        logger.exception(f'Failed to create celery audit log: {e}')
