"""
Microsoft Graph API email backend for Django.

Credentials are loaded from the EmailConfig database record first.
Falls back to Django settings (AZURE_AD_*  + GRAPH_MAIL_SENDER) if the
database record is incomplete or unavailable.
"""
import logging
import json
import msal
import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"


def _load_credentials():
    """Return (tenant_id, client_id, client_secret, sender) from DB or settings fallback."""
    try:
        from apps.notifications.models import EmailConfig
        cfg = EmailConfig.objects.filter(pk=1).first()
        if cfg and cfg.is_configured:
            return cfg.tenant_id, cfg.client_id, cfg.get_secret(), cfg.sender_email
    except Exception as e:
        logger.warning(f"Could not load EmailConfig from DB: {e}")

    return (
        getattr(settings, 'AZURE_AD_TENANT_ID', ''),
        getattr(settings, 'AZURE_AD_CLIENT_ID', ''),
        getattr(settings, 'AZURE_AD_CLIENT_SECRET', ''),
        getattr(settings, 'GRAPH_MAIL_SENDER', ''),
    )


def _get_access_token(tenant_id, client_id, client_secret):
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "unknown"))
        raise RuntimeError(f"Failed to acquire Graph API token: {error}")
    return result["access_token"]


def _build_message(email_message):
    to_recipients = [{"emailAddress": {"address": a}} for a in email_message.to]
    cc_recipients = [{"emailAddress": {"address": a}} for a in (email_message.cc or [])]
    bcc_recipients = [{"emailAddress": {"address": a}} for a in (email_message.bcc or [])]

    body_content = email_message.body
    body_type = "Text"
    if hasattr(email_message, "alternatives"):
        for content, mimetype in email_message.alternatives:
            if mimetype == "text/html":
                body_content = content
                body_type = "HTML"
                break

    payload = {
        "message": {
            "subject": email_message.subject,
            "body": {"contentType": body_type, "content": body_content},
            "toRecipients": to_recipients,
        },
        "saveToSentItems": "false",
    }
    if cc_recipients:
        payload["message"]["ccRecipients"] = cc_recipients
    if bcc_recipients:
        payload["message"]["bccRecipients"] = bcc_recipients
    return payload


class GraphEmailBackend(BaseEmailBackend):
    """Send email via Microsoft Graph API using app-only (client credentials) auth."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        tenant_id, client_id, client_secret, sender = _load_credentials()

        if not all([tenant_id, client_id, client_secret, sender]):
            logger.error("Graph email backend: incomplete credentials — email not sent.")
            return 0

        try:
            token = _get_access_token(tenant_id, client_id, client_secret)
        except Exception as e:
            logger.exception(f"Graph API token acquisition failed: {e}")
            if not self.fail_silently:
                raise
            return 0

        sent = 0
        url = GRAPH_SEND_URL.format(sender=sender)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        for message in email_messages:
            try:
                payload = _build_message(message)
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
                if response.status_code == 202:
                    sent += 1
                    logger.info(f"Graph email sent to {message.to} — subject: {message.subject!r}")
                else:
                    logger.error(
                        f"Graph API sendMail failed [{response.status_code}]: {response.text[:300]}"
                    )
                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.exception(f"Failed to send email to {message.to}: {e}")
                if not self.fail_silently:
                    raise

        return sent
