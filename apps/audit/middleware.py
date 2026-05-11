"""
Lightweight middleware — heavy audit is done per-action in views.
This middleware only tags API calls automatically.
"""

AUDIT_API_PATHS = ['/api/v1/']


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if any(request.path.startswith(p) for p in AUDIT_API_PATHS):
            if request.user.is_authenticated and request.method not in ('GET', 'HEAD', 'OPTIONS'):
                from .utils import log_action
                log_action(
                    request, 'API_CALL', 'api',
                    description=f'{request.method} {request.path}',
                    extra_data={'status_code': response.status_code},
                )
        return response
