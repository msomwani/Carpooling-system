from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.common.db import get_db
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_overview(db, days=days)


@router.get("/me")
def analytics_me(
    role: Literal["passenger", "driver"] = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_personal_analytics(db, user_id=user_id, role=role)
