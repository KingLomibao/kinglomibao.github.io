from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.relief import get_relief_due
from app.schemas.relief import ReliefDueItemSchema

router = APIRouter(prefix="/api/relief", tags=["relief"])


@router.get("/due", response_model=list[ReliefDueItemSchema])
def read_relief_due(
    window_days: int = Query(default=None, ge=1, le=365, description="Defaults to the configured relief window."),
    db: Session = Depends(get_db),
) -> list[ReliefDueItemSchema]:
    items = get_relief_due(db, window_days=window_days)
    return [ReliefDueItemSchema.from_domain(i) for i in items]
