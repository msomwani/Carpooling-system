from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.common.db import SessionLocal
from app.auth.schemas import (
    SignupRequest,
    LoginRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    GoogleAuthRequest,
)
from app.auth.service import AuthService
from app.auth.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _set_auth_cookie(response: Response, user_id: str) -> None:
    token = create_access_token(subject=user_id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,   # Set to True in production (HTTPS)
        samesite="lax",
    )


@router.post("/signup", status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user. Sends an OTP to verify the email."""
    try:
        user = AuthService.signup(db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "message": "Account created. Please check your email for the OTP to verify your account.",
        "email": user.email,
    }


@router.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)):
    """Verify an OTP code. On success, logs the user in."""
    try:
        user = AuthService.verify_otp(db, email=payload.email, otp=payload.otp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _set_auth_cookie(response, str(user.id))
    return {"message": "Email verified successfully. You are now logged in."}


@router.post("/resend-otp")
def resend_otp(payload: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend a fresh OTP to the given email."""
    try:
        AuthService.resend_otp(db, email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "A new OTP has been sent to your email."}


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Standard email+password login. Rejects accounts that are not verified."""
    user = AuthService.authenticate(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox for the OTP or request a new one at /auth/resend-otp",
        )

    _set_auth_cookie(response, str(user.id))
    return {"message": "Logged in"}


@router.post("/google")
def google_login(payload: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    """Sign in or sign up using a Google ID token from the frontend."""
    try:
        user = AuthService.google_auth(db, id_token=payload.id_token, role=payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    _set_auth_cookie(response, str(user.id))
    return {"message": "Logged in via Google", "name": user.name, "email": user.email}
