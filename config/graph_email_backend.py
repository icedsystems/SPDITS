"""
Microsoft Graph API email backend for Django.

Uses Azure client credentials (tenant ID + client ID + client secret) to obtain
an OAuth2 token, then sends email via the Graph API /sendMail endpoint.

Required settings:
  AZURE_AD_TENANT_ID     — Azure tenant ID
  AZURE_AD_CLIENT_ID     — App registration client ID
  AZURE_AD_CLIENT_SECRET — App registration client secret
  GRAPH_MAIL_SENDER      — The licensed mailbox to send from (e.g. noreply@iced-eval.org)
                           Must have Mail.Send application permission granted in Azure.
"""
import logging
import json
import msal
import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"


def _get_access_token():
    app = msal.ConfidentialClientApplication(
        client_id=settings.AZURE_AD_CLIENT_ID,
        client_credential=settings.AZURE_AD_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}",
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "unknown"))
        raise RuntimeError(f"Failed to acquire Graph API token: {error}")
    return result["access_token"]


def _build_message(email_message):
    """Convert a Django EmailMessage into a Graph API sendMail payload."""
    to_recipients = [
        {"emailAddress": {"address": addr}} for addr in email_message.to
    ]
    cc_recipients = [
        {"emailAddress": {"address": addr}} for addr in (email_message.cc or [])
    ]
    bcc_recipients = [
        {"emailAddress": {"address": addr}} for addr in (email_message.bcc or [])
    ]

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
            "body": {
                "contentType": body_type,
                "content": body_content,
            },
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

        sender = getattr(settings, "GRAPH_MAIL_SENDER", "")
        if not sender:
            logger.error("GRAPH_MAIL_SENDER is not set — cannot send email via Graph API.")
            return 0

        try:
            token = _get_access_token()
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
