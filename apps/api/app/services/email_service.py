from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


class EmailDeliveryError(RuntimeError):
    pass


def send_password_reset_email(
    *,
    recipient_email: str,
    reset_url: str,
    expires_minutes: int,
) -> None:
    settings = get_settings()

    if not settings.smtp_host:
        raise EmailDeliveryError("SMTP host is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your EV Smart Charging password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient_email

    message.set_content(
        "\n".join(
            [
                "EV Smart Charging password reset",
                "",
                "Use the secure link below to set a new password:",
                "",
                reset_url,
                "",
                f"This link expires in {expires_minutes} minutes.",
                "",
                "If you did not request this reset, ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_starttls:
                smtp.starttls()

            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)

            smtp.send_message(message)
    except Exception as exc:
        raise EmailDeliveryError("Could not send password reset email") from exc
