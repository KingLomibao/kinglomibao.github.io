from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.staffing import get_staffing_coverage, get_staffing_shortages
from app.schemas.site import StaffingCoverageSchema

router = APIRouter(prefix="/api/staffing", tags=["staffing"])


@router.get("/coverage", response_model=list[StaffingCoverageSchema])
def read_staffing_coverage(db: Session = Depends(get_db)) -> list[StaffingCoverageSchema]:
    return [StaffingCoverageSchema.from_domain(c) for c in get_staffing_coverage(db)]


@router.get("/shortages", response_model=list[StaffingCoverageSchema])
def read_staffing_shortages(db: Session = Depends(get_db)) -> list[StaffingCoverageSchema]:
    return [StaffingCoverageSchema.from_domain(c) for c in get_staffing_shortages(db)]
