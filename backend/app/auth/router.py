from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.common.db import SessionLocal
from app.auth.schemas import SignupRequest, LoginRequest
from app.auth.service import AuthService
from app.auth.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    user = AuthService.signup(db, **payload.model_dump())
    return {"id": user.id}


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate(db, **payload.model_dump())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id))
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # True in production
        samesite="lax"
    )
    return {"message": "Logged in"}
