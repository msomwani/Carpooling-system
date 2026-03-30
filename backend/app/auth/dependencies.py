from fastapi import Cookie, HTTPException
from jose import jwt, JWTError
from typing import Optional

from app.config.settings import settings

ALGORITHM = "HS256"
_COOKIE_NAME = "access_token"


def get_current_user_id(access_token: Optional[str] = Cookie(default=None)) -> str:
    """Extract and validate the JWT from the HTTP-only 'access_token' cookie.

    Using a cookie (instead of Authorization header) prevents XSS attacks from
    stealing the token, since HTTP-only cookies are inaccessible to JavaScript.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token (missing subject)")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token (decoding failed)")
