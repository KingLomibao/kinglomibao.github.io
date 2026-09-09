from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment
from app.schemas.assignment import AssignmentSchema

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentSchema])
def list_assignments(
    status: str | None = None,
    site_id: int | None = None,
    role_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[AssignmentSchema]:
    query = db.query(Assignment)
    if status is not None:
        query = query.filter(Assignment.status == status)
    if site_id is not None:
        query = query.filter(Assignment.site_id == site_id)
    if role_id is not None:
        query = query.filter(Assignment.role_id == role_id)

    assignments = query.order_by(Assignment.start_date.desc()).all()
    return [AssignmentSchema.from_orm_assignment(a) for a in assignments]


@router.get("/{assignment_id}", response_model=AssignmentSchema)
def read_assignment(assignment_id: int, db: Session = Depends(get_db)) -> AssignmentSchema:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found.")
    return AssignmentSchema.from_orm_assignment(assignment)
