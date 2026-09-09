from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WorkforceMovement
from app.schemas.movement import WorkforceMovementSchema

router = APIRouter(prefix="/api/movements", tags=["movements"])


@router.get("/upcoming", response_model=list[WorkforceMovementSchema])
def list_upcoming_movements(
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[WorkforceMovementSchema]:
    today = date.today()
    window_end = today + timedelta(days=window_days)
    movements = (
        db.query(WorkforceMovement)
        .filter(WorkforceMovement.movement_date >= today, WorkforceMovement.movement_date <= window_end)
        .order_by(WorkforceMovement.movement_date)
        .all()
    )
    return [WorkforceMovementSchema.from_orm_movement(m) for m in movements]
