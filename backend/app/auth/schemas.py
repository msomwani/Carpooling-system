from pydantic import BaseModel, EmailStr
from typing import Literal


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["driver", "passenger"] = "passenger"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class GoogleAuthRequest(BaseModel):
    id_token: str
    role: Literal["driver", "passenger"] = "passenger"
