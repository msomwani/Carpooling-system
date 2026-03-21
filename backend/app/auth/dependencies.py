from fastapi import Request, HTTPException
from jose import jwt, JWTError

from app.config.settings import settings

ALGORITHM = "HS256"

def get_current_user_id(request: Request) -> str:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token (missing subject)")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token (decoding failed)")
