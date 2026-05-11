from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    from apps.audit.utils import log_action
    from .models import UserSession
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    ua = request.META.get('HTTP_USER_AGENT', '')
    UserSession.objects.create(
        user=user,
        session_key=request.session.session_key or '',
        ip_address=ip or None,
        user_agent=ua,
    )
    user.last_activity = timezone.now()
    user.save(update_fields=['last_activity'])
    log_action(request, 'LOGIN', 'accounts', user.pk, description=f'User {user.email} logged in')


@receiver(user_logged_out)
def on_user_logout(sender, request, user, **kwargs):
    from apps.audit.utils import log_action
    if user:
        UserSession.objects.filter(
            user=user,
            session_key=request.session.session_key or '',
            is_active=True
        ).update(is_active=False, logout_at=timezone.now())
        log_action(request, 'LOGOUT', 'accounts', user.pk, description=f'User {user.email} logged out')


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    from apps.audit.utils import log_action
    email = credentials.get('email', credentials.get('username', 'unknown'))
    log_action(request, 'LOGIN_FAILED', 'accounts', description=f'Failed login attempt for {email}')
