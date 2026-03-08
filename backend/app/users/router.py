from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.users.service import UserService
from app.users.schemas import RoleUpdateRequest
from app.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/users", tags=["Users"])



@router.patch("/me/role")
def update_my_role(
    payload: RoleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        user = UserService.update_role(db, user_id=user_id, role=payload.role)
        return {"message": f"Role successfully updated to {user.role}", "role": user.role}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
