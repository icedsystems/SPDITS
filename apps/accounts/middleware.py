from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
import datetime


class ForcePasswordChangeMiddleware:
    """Redirect any authenticated user whose force_password_change flag is set."""

    EXEMPT_PATHS = [
        '/accounts/set-password/',
        '/accounts/logout/',
        '/accounts/login/',
        '/accounts/oauth/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'force_password_change', False):
            if not any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
                return redirect('/accounts/set-password/')
        return self.get_response(request)


class SessionTimeoutMiddleware:
    """Automatically log out idle users after SESSION_TIMEOUT_SECONDS."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 1800)

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity_str = request.session.get('last_activity')
            if last_activity_str:
                last_activity = datetime.datetime.fromisoformat(last_activity_str)
                now = timezone.now()
                elapsed = (now - last_activity).total_seconds()
                if elapsed > self.timeout:
                    logout(request)
                    return redirect(settings.LOGIN_URL + '?timeout=1')
            request.session['last_activity'] = timezone.now().isoformat()
        return self.get_response(request)
