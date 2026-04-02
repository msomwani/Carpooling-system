import logging
from sqlalchemy.orm import Session

from app.users.models import User
from app.config.settings import settings

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def google_auth(db: Session, *, id_token: str) -> User:
        """Verify Google ID token and log in or create the user."""
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        if not settings.google_client_id:
            raise RuntimeError(
                "Google OAuth is not configured (GOOGLE_CLIENT_ID missing)"
            )

        try:
            id_info = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
            # Explicitly verify properties for extra security
            if id_info.get("aud") != settings.google_client_id:
                raise ValueError("Token audience mismatch")
            if id_info.get("iss") not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise ValueError("Token issuer mismatch")
        except Exception as exc:
            logger.error(f"Invalid Google token: {exc}")
            raise ValueError(f"Invalid Google token: {exc}")

        email = id_info.get("email")
        if not email:
            raise ValueError("Google token did not include an email address")
        name = id_info.get("name", email)

        user = db.query(User).filter(User.email == email).first()
        if not user:
            # First-time Google sign-in — create account, skip OTP
            user = User(
                name=name,
                email=email,
                password_hash=None,  # no password for Google users
                role="passenger",  # Hardcode as passenger to prevent privilege escalation
                is_email_verified=True,  # Google already verified it
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        return user
