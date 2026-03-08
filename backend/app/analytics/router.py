from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_overview(db, days=days)

