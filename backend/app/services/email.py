"""Asynchronous SMTP delivery for account-verification messages."""

from email.message import EmailMessage
from html import escape
from urllib.parse import urlencode

import aiosmtplib

from app.core.config import settings


async def send_verification_email(email: str, full_name: str, token: str) -> None:
    """Deliver a verification link through the configured SMTP relay."""
    query = urlencode({"verify_token": token})
    verification_url = f"{settings.frontend_base_url}/?{query}"
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message["Subject"] = "Verify your AapdaSetu email"
    message.set_content(
        f"Hello {full_name},\n\n"
        "Verify your AapdaSetu email address using this link:\n"
        f"{verification_url}\n\n"
        f"This link expires in {settings.email_verification_token_minutes} minutes. "
        "If you did not create this account, you can ignore this message."
    )
    message.add_alternative(
        "<p>Hello "
        f"{escape(full_name)},</p><p>Verify your AapdaSetu email address:</p>"
        f'<p><a href="{escape(verification_url, quote=True)}">Verify email</a></p>'
        f"<p>This link expires in {settings.email_verification_token_minutes} minutes. "
        "If you did not create this account, you can ignore this message.</p>",
        subtype="html",
    )
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        timeout=10,
    )
