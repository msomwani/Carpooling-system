from sqlalchemy.orm import Session
from app.users.models import User

class UserService:

    @staticmethod
    def get_user(db: Session, *, user_id: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        return user

    @staticmethod
    def update_role(db: Session, *, user_id: str, role: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
            
        user.role = role
        db.commit()
        db.refresh(user)
        return user
