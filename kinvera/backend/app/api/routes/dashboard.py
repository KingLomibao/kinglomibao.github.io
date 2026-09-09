from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.dashboard import get_dashboard_summary
from app.schemas.dashboard import DashboardSummarySchema

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummarySchema)
def read_dashboard_summary(
    relief_window_days: int = Query(default=None, ge=1, le=365),
    db: Session = Depends(get_db),
) -> DashboardSummarySchema:
    summary = get_dashboard_summary(db, relief_window_days=relief_window_days)
    return DashboardSummarySchema.from_domain(summary)
