from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.db import SessionLocal
from app.users.models import User
from app.users.schemas import RoleUpdateRequest
from app.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.patch("/me/role")
def update_my_role(
    payload: RoleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Change the user's active role preference (driver or passenger)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = payload.role
    db.commit()
    db.refresh(user)
    
    return {"message": f"Role successfully updated to {user.role}", "role": user.role}
