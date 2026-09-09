from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.simulation import AssignmentNotFoundError, simulate_extension
from app.schemas.simulation import ExtensionSimulationRequestSchema, ExtensionSimulationResponseSchema

router = APIRouter(prefix="/api/assignments", tags=["simulation"])


@router.post("/{assignment_id}/simulate-extension", response_model=ExtensionSimulationResponseSchema)
def simulate_assignment_extension(
    assignment_id: int,
    request: ExtensionSimulationRequestSchema,
    db: Session = Depends(get_db),
) -> ExtensionSimulationResponseSchema:
    """Preview the downstream impact of extending an assignment.

    This is a read-only, deterministic scenario calculation - calling
    it never changes the assignment or any other record.
    """
    try:
        result = simulate_extension(db, assignment_id, request.extension_days)
    except AssignmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExtensionSimulationResponseSchema.from_domain(result)
