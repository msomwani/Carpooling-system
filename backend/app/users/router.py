from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.users.service import UserService
from app.users.schemas import RoleUpdateRequest, UserResponse
from app.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        user = UserService.get_user(db, user_id=user_id)
        return user
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/me/role")
def update_my_role(
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        user = UserService.update_role(db, user_id=user_id, role=payload.role)
        return {"message": f"Role successfully updated to {user.role}", "role": user.role}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
