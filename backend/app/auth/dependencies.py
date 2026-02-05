from fastapi import Cookie, HTTPException
from jose import jwt, JWTError

from app.config.settings import settings

ALGORITHM = "HS256"


def get_current_user_id(
    access_token: str | None = Cookie(default=None)
) -> str:
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
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
