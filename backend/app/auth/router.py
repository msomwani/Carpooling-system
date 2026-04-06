from fastapi import APIRouter, Depends, HTTPException, Response, Request
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth.schemas import GoogleAuthRequest
from app.auth.service import AuthService
from app.auth.security import create_access_token, create_refresh_token, ALGORITHM

from app.config.settings import settings

# Rate limiter: 10 login attempts per minute per IP.
# In production, uses Redis for distributed storage.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url if settings.redis_url else "memory://",
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

_ACCESS_COOKIE_NAME = "access_token"
_ACCESS_COOKIE_MAX_AGE = 15 * 60  # 15 minutes in seconds

_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


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
    except ValueError as e:
        logger.warning(f"Google login validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")
    except RuntimeError as e:
        logger.error(f"Google login service runtime error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error during google sync: {str(e)}", exc_info=True)
        raise  # Let generic handler take it

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # Set the access token as an HTTP-only cookie (short‑lived)
    response.set_cookie(
        key=_ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=_ACCESS_COOKIE_MAX_AGE,
        path="/",
    )
    # Set the refresh token as an HTTP-only cookie (long‑lived)
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=_REFRESH_COOKIE_MAX_AGE,
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
    """Clear both authentication cookies (access & refresh)."""
    response.delete_cookie(key=_ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path="/")
    return {"detail": "Logged out successfully"}


@router.post("/refresh-token")
def refresh_token_endpoint(response: Response, request: Request):
    """Issue a new short‑lived access token using a valid refresh token.

    The refresh token is stored in an HTTP‑only cookie named `_REFRESH_COOKIE_NAME`.
    It must have a payload `{"type": "refresh"}` to be accepted.
    """
    refresh_cookie = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            refresh_cookie,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token type")
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Issue a new short‑lived access token
    new_access = create_access_token(user_id)
    response.set_cookie(
        key=_ACCESS_COOKIE_NAME,
        value=new_access,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=_ACCESS_COOKIE_MAX_AGE,
        path="/",
    )
    return {"detail": "Access token refreshed"}
