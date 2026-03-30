from fastapi import APIRouter, Depends, HTTPException, Response, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth.schemas import GoogleAuthRequest
from app.auth.service import AuthService
from app.auth.security import create_access_token

# Rate limiter: 10 login attempts per minute per IP.
# In production, swap storage_uri to Redis: "redis://localhost:6379"
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Auth"])

_COOKIE_NAME = "access_token"
# 30 days in seconds
_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


@router.post("/sync-google-user")
@limiter.limit("10/minute")
def sync_google_user(
    request: Request,
    payload: GoogleAuthRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Sync/check a Google user for NextAuth Google Provider."""
    try:
        user = AuthService.google_auth(db, id_token=payload.id_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Authentication failed")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service unavailable")

    token = create_access_token(str(user.id))

    # Set the JWT as an HTTP-only cookie so it is inaccessible to JavaScript.
    # SameSite='lax' blocks cross-site POST requests (CSRF protection).
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # Set to True in production (HTTPS only)
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )

    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        # Token is intentionally NOT returned in the body.
        # The browser will store it automatically in the HTTP-only cookie.
    }


@router.post("/logout")
def logout(response: Response):
    """Clear the authentication cookie to log the user out.

    Because the cookie is HTTP-only, JavaScript cannot delete it.
    The frontend must call this endpoint so the server can expire it.
    """
    response.delete_cookie(key=_COOKIE_NAME, path="/")
    return {"detail": "Logged out successfully"}
