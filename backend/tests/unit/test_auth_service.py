import pytest
from unittest.mock import patch
from app.auth.service import AuthService
from app.users.models import User

class TestAuthService:
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
