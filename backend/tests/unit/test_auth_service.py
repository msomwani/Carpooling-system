import pytest
from unittest.mock import patch
from app.auth.service import AuthService
from app.users.models import User

class TestAuthService:
    def test_signup_email_failure_orphans_user_reproduction(self, db):
        """
        REPRODUCTION: Verify that currently, a user is created in the DB 
        even if the email sending fails.
        """
        email = "fail-email@test.com"
        
        # Verify user doesn't exist
        assert db.query(User).filter(User.email == email).first() is None
        
        # Mock send_otp_email to fail
        with patch("app.auth.service.send_otp_email") as mock_send:
            mock_send.side_effect = RuntimeError("Email delivery failed")
            
            with pytest.raises(RuntimeError, match="Email delivery failed"):
                AuthService.signup(
                    db=db,
                    name="Fail User",
                    email=email,
                    password="password123",
                    role="passenger"
                )
        
        # Verify fix: user should NOT EXIST in DB if sign-up failure occurred
        orphaned_user = db.query(User).filter(User.email == email).first()
        assert orphaned_user is None

    def test_google_auth_always_defaults_to_passenger(self, db):
        """Issue 5: Verify that Google OAuth always creates users as 'passenger' regardless of input."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "email": "google-user@test.com",
                "name": "Google User",
                "sub": "google-sub-123"
            }
            
            # Act: Sign in via Google OAuth (role is now ignored/removed from API)
            user = AuthService.google_auth(
                db=db,
                id_token="fake-token"
            )
            
            # Assert: Role should still be 'passenger'
            assert user.role == "passenger"
            
            # Verify in DB
            db_user = db.query(User).filter(User.email == "google-user@test.com").first()
            assert db_user.role == "passenger"
