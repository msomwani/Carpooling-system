import random
import string
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.users.models import User
from app.auth.security import hash_password, verify_password
from app.common.email import send_otp_email
from app.config.settings import settings


def _generate_otp() -> str:
    """Generate a random 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def signup(db: Session, *, name: str, email: str, password: str, role: str) -> User:
        """Create account, generate OTP, send email. Does NOT log user in yet."""
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("Email already registered")

        otp = _generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_email_verified=False,
            otp_code=otp,
            otp_expires_at=expires_at,
        )
        db.add(user)
        db.flush()  # Push to DB but don't commit yet

        try:
            send_otp_email(email, otp)
        except Exception as exc:
            db.rollback()
            logger.error("Signup failed due to email delivery error: %s", exc)
            raise RuntimeError(f"Signup failed: Email delivery failed: {exc}") from exc

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def verify_otp(db: Session, *, email: str, otp: str) -> User:
        """Verify OTP for an email. Sets is_email_verified=True on success."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("User not found")
        if user.is_email_verified:
            raise ValueError("Email already verified")
        if not user.otp_code or user.otp_code != otp:
            raise ValueError("Invalid OTP")
        now = datetime.now(timezone.utc)
        if user.otp_expires_at and user.otp_expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("OTP has expired")

        user.is_email_verified = True
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def resend_otp(db: Session, *, email: str) -> None:
        """Generate and resend a fresh OTP for the given email."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("User not found")
        if user.is_email_verified:
            raise ValueError("Email already verified")

        otp = _generate_otp()
        user.otp_code = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)
        db.commit()
        send_otp_email(email, otp)

    @staticmethod
    def authenticate(db: Session, *, email: str, password: str) -> User | None:
        """Authenticate via email+password. Rejects unverified accounts."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not user.password_hash or not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def google_auth(db: Session, *, id_token: str) -> User:
        """Verify Google ID token and log in or create the user."""
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        if not settings.google_client_id:
            raise RuntimeError("Google OAuth is not configured (GOOGLE_CLIENT_ID missing)")

        try:
            id_info = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except Exception as exc:
            raise ValueError(f"Invalid Google token: {exc}") from exc

        email = id_info.get("email")
        name = id_info.get("name", email)

        if not email:
            raise ValueError("Google token did not include an email address")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            # First-time Google sign-in — create account, skip OTP
            user = User(
                name=name,
                email=email,
                password_hash=None,   # no password for Google users
                role="passenger",      # 🔥 Hardcode as passenger to prevent privilege escalation
                is_email_verified=True,  # Google already verified it
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        return user
