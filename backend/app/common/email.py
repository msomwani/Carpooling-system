"""
Email sending utility using AWS SES via SMTP.

If SMTP is not configured (SMTP_SERVER is empty), the OTP/email is
printed to the console so you can still test the full flow locally
without a real email provider.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.smtp_server and settings.smtp_username and settings.smtp_password)


def send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP code to the given email address.

    Falls back to console logging when SMTP is not configured.
    """
    subject = "Your Carpooling OTP Code"
    body_html = f"""
    <html><body>
      <p>Hello,</p>
      <p>Your OTP for the Carpooling app is:</p>
      <h2 style="letter-spacing:8px;font-size:36px;font-family:monospace">{otp}</h2>
      <p>This code expires in <strong>{settings.otp_expiry_minutes} minutes</strong>.</p>
      <p>If you did not request this, please ignore this email.</p>
    </body></html>
    """

    if not _smtp_configured():
        # Dev fallback: print to console
        logger.warning(
            "[MockEmail] SMTP not configured. OTP for %s: %s", to_email, otp
        )
        print(f"\n{'='*50}")
        print(f"[MockEmail] To: {to_email}")
        print(f"[MockEmail] OTP: {otp}")
        print(f"{'='*50}\n")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        logger.info("OTP email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise RuntimeError(f"Email delivery failed: {exc}") from exc
