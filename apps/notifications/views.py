import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView
from .models import Notification, EmailConfig

logger = logging.getLogger(__name__)


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return self.request.user.notifications.order_by('-created_at')


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = request.user.notifications.filter(pk=pk).first()
        if notif:
            notif.mark_read()
        if request.htmx:
            return JsonResponse({'status': 'ok'})
        return redirect('notifications:list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        from django.utils import timezone
        request.user.notifications.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect('notifications:list')


class EmailConfigView(LoginRequiredMixin, View):
    template_name = 'notifications/email_config.html'

    def _admin_required(self, request):
        if not request.user.is_admin():
            messages.error(request, 'Only administrators can access email settings.')
            return redirect('dashboards:home')
        return None

    def get(self, request):
        guard = self._admin_required(request)
        if guard:
            return guard
        config = EmailConfig.get()
        return render(request, self.template_name, {'config': config})

    def post(self, request):
        guard = self._admin_required(request)
        if guard:
            return guard

        action = request.POST.get('action', 'save')
        config = EmailConfig.get()

        if action == 'save':
            config.tenant_id = request.POST.get('tenant_id', '').strip()
            config.client_id = request.POST.get('client_id', '').strip()
            config.sender_email = request.POST.get('sender_email', '').strip()
            new_secret = request.POST.get('client_secret', '').strip()
            if new_secret:
                config.set_secret(new_secret)
            config.save()
            messages.success(request, 'Email configuration saved.')
            return redirect('notifications:email_config')

        elif action == 'test':
            recipient = request.POST.get('test_recipient', '').strip()
            if not recipient:
                messages.error(request, 'Enter a recipient email address to send the test.')
                return redirect('notifications:email_config')
            if not config.is_configured:
                messages.error(request, 'Save valid credentials before sending a test.')
                return redirect('notifications:email_config')
            try:
                _send_test_email(config, recipient)
                messages.success(request, f'Test email sent to {recipient}. Check the inbox.')
            except Exception as e:
                logger.exception(f'Test email failed: {e}')
                messages.error(request, f'Test email failed: {e}')
            return redirect('notifications:email_config')

        return redirect('notifications:email_config')


def _send_test_email(config, recipient):
    """Send a test email using the stored Graph config directly (bypass Django backend)."""
    import json
    import msal
    import requests

    app = msal.ConfidentialClientApplication(
        client_id=config.client_id,
        client_credential=config.get_secret(),
        authority=f"https://login.microsoftonline.com/{config.tenant_id}",
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "unknown"))
        raise RuntimeError(f"Token error: {error}")

    token = result["access_token"]
    url = f"https://graph.microsoft.com/v1.0/users/{config.sender_email}/sendMail"
    payload = {
        "message": {
            "subject": "ICED SPDITS — Email Configuration Test",
            "body": {
                "contentType": "HTML",
                "content": (
                    "<p>This is a test message from <strong>ICED SPDITS</strong>.</p>"
                    "<p>Your Microsoft Graph API email configuration is working correctly.</p>"
                    "<hr><small>Sent from ICED SPDITS Email Notification Settings</small>"
                ),
            },
            "toRecipients": [{"emailAddress": {"address": recipient}}],
        },
        "saveToSentItems": "false",
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=15,
    )
    if resp.status_code != 202:
        raise RuntimeError(f"Graph API returned {resp.status_code}: {resp.text[:300]}")
