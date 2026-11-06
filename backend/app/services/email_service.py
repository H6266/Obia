import html
import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
RESEND_EMAILS_URL = "https://api.resend.com/emails"


class EmailDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailContent:
    subject: str
    html: str
    text: str


def _wrap(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html>
  <body style=\"margin:0;padding:0;background:#f6f7f9;font-family:Arial,Helvetica,sans-serif;color:#111827;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"padding:24px 12px;\">
      <tr><td align=\"center\">
        <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:560px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;\">
          <tr><td style=\"padding:24px 24px 8px 24px;\">
            <div style=\"font-size:22px;font-weight:700;letter-spacing:0.02em;color:#111827;\">Obia</div>
            <h1 style=\"margin:16px 0 0 0;font-size:20px;line-height:1.3;color:#111827;\">{safe_title}</h1>
          </td></tr>
          <tr><td style=\"padding:8px 24px 24px 24px;font-size:15px;line-height:1.6;color:#374151;\">{body}</td></tr>
          <tr><td style=\"padding:16px 24px;background:#f9fafb;font-size:12px;line-height:1.5;color:#6b7280;\">
            Obia will never ask for your code by phone or in a message reply. If you did not request this, you can ignore this email.
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


def verification_email(*, code: str, verify_url: str) -> EmailContent:
    safe_code = html.escape(code)
    safe_url = html.escape(verify_url)
    body = f"""
      <p>Use this code to verify your Obia email address:</p>
      <p style=\"margin:20px 0;text-align:center;\"><span style=\"display:inline-block;padding:14px 18px;border-radius:10px;background:#111827;color:#ffffff;font-size:28px;letter-spacing:0.22em;font-weight:700;\">{safe_code}</span></p>
      <p>This code expires in <strong>10 minutes</strong>. Do not share this code with anyone.</p>
      <p><a href=\"{safe_url}\" style=\"color:#111827;font-weight:600;\">Return to Obia verification</a></p>
    """
    return EmailContent(
        subject="Verify your Obia email address",
        html=_wrap("Verify your email address", body),
        text=(
            "Obia - Verify your email address\n\n"
            f"Your verification code is: {code}\n"
            "This code expires in 10 minutes. Do not share this code with anyone.\n"
            f"Verify at: {verify_url}\n\n"
            "Obia will never ask for your code by phone."
        ),
    )


def password_recovery_email(*, code: str) -> EmailContent:
    safe_code = html.escape(code)
    body = f"""
      <p>Use this code to reset your Obia password:</p>
      <p style=\"margin:20px 0;text-align:center;\"><span style=\"display:inline-block;padding:14px 18px;border-radius:10px;background:#111827;color:#ffffff;font-size:28px;letter-spacing:0.22em;font-weight:700;\">{safe_code}</span></p>
      <p>This code expires in <strong>10 minutes</strong>.</p>
      <p><strong>Warning:</strong> Obia will never ask for this code by phone. Do not share it with anyone.</p>
    """
    return EmailContent(
        subject="Reset your Obia password",
        html=_wrap("Password recovery", body),
        text=(
            "Obia - Password recovery\n\n"
            f"Your recovery code is: {code}\n"
            "This code expires in 10 minutes.\n"
            "Warning: Obia will never ask for this code by phone. Do not share it."
        ),
    )


def login_otp_email(*, code: str, account_label: str = "Obia account") -> EmailContent:
    safe_code = html.escape(code)
    safe_label = html.escape(account_label)
    body = f"""
      <p>Use this code to complete sign-in to your {safe_label}:</p>
      <p style=\"margin:20px 0;text-align:center;\"><span style=\"display:inline-block;padding:14px 18px;border-radius:10px;background:#111827;color:#ffffff;font-size:28px;letter-spacing:0.22em;font-weight:700;\">{safe_code}</span></p>
      <p>This code expires in <strong>10 minutes</strong>. Do not share this code with anyone.</p>
      <p>If you did not try to sign in, you can ignore this email and consider changing your password.</p>
    """
    return EmailContent(
        subject="Your Obia sign-in code",
        html=_wrap("Sign-in verification code", body),
        text=(
            "Obia - Sign-in verification code\n\n"
            f"Your sign-in code is: {code}\n"
            "This code expires in 10 minutes. Do not share this code with anyone.\n"
            "If you did not try to sign in, ignore this email and consider changing your password.\n\n"
            "Obia will never ask for your code by phone."
        ),
    )


def password_changed_email() -> EmailContent:
    body = """
      <p>Your Obia account password was changed successfully.</p>
      <p>If you made this change, no further action is needed. If you did not make this change, reset your password immediately and contact Obia support.</p>
    """
    return EmailContent(
        subject="Your Obia password was changed",
        html=_wrap("Password changed", body),
        text=(
            "Obia - Password changed\n\n"
            "Your Obia account password was changed successfully.\n"
            "If you did not make this change, reset your password immediately and contact support."
        ),
    )


def send_email(*, to: str, content: EmailContent) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.email_from:
        raise EmailDeliveryError("Email delivery is not configured.")
    try:
        response = httpx.post(
            RESEND_EMAILS_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": content.subject,
                "html": content.html,
                "text": content.text,
            },
            timeout=10.0,
        )
    except httpx.HTTPError as error:
        logger.warning("Email delivery request failed for a recipient.")
        raise EmailDeliveryError("Could not send the email right now.") from error

    if response.status_code >= 400:
        logger.warning("Email provider returned an unsuccessful response.")
        raise EmailDeliveryError("Could not send the email right now.")
