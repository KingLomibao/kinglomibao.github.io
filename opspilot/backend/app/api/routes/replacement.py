from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.replacement import AssignmentNotFoundError, find_replacement_candidates
from app.schemas.replacement import ReplacementSearchResponseSchema

router = APIRouter(prefix="/api/assignments", tags=["replacement"])


@router.get("/{assignment_id}/replacement-candidates", response_model=ReplacementSearchResponseSchema)
def read_replacement_candidates(assignment_id: int, db: Session = Depends(get_db)) -> ReplacementSearchResponseSchema:
    try:
        result = find_replacement_candidates(db, assignment_id)
    except AssignmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReplacementSearchResponseSchema.from_domain(result)
