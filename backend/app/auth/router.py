from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.auth.schemas import GoogleAuthRequest
from app.auth.service import AuthService
from app.auth.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/sync-google-user")
def sync_google_user(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Sync/check a Google user for NextAuth Google Provider."""
    try:
        user = AuthService.google_auth(db, id_token=payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Authentication failed")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Service unavailable")

    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "token": create_access_token(str(user.id)),
    }
