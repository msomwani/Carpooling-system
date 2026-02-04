from sqlalchemy.orm import Session
from app.users.models import User
from app.auth.security import hash_password, verify_password


class AuthService:

    @staticmethod
    def signup(db: Session, *, name, email, password, role):
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, *, email, password):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
