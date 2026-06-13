import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services.email_templates import (
    build_password_reset_url,
    render_password_reset_body,
    render_password_reset_subject,
)


logger = logging.getLogger("app.email")


class EmailDeliveryError(RuntimeError):
    pass


class SMTPEmailProvider:
    def send_email(self, recipient: str, subject: str, body: str) -> None:
        if not settings.smtp_host:
            raise EmailDeliveryError("SMTP_HOST is not configured")

        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_username:
                    smtp.starttls()
                    smtp.login(settings.smtp_username, settings.smtp_password)

                smtp.send_message(message)
        except OSError as exc:
            raise EmailDeliveryError("Failed to send email") from exc


class EmailService:
    def __init__(self, provider: SMTPEmailProvider | None = None) -> None:
        self.provider = provider or SMTPEmailProvider()

    def send_password_reset_email(self, recipient: str, raw_token: str) -> None:
        reset_url = build_password_reset_url(settings.password_reset_url, raw_token)
        subject = render_password_reset_subject()
        body = render_password_reset_body(reset_url)

        self.provider.send_email(recipient, subject, body)
        logger.info(
            "password_reset_email_sent",
            extra={"recipient": recipient},
        )


def get_email_service() -> EmailService:
    return EmailService()
