from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.qualifications import list_qualification_risks
from app.schemas.qualification_risk import QualificationRiskSchema

router = APIRouter(prefix="/api/qualifications", tags=["qualifications"])


@router.get("/risks", response_model=list[QualificationRiskSchema])
def read_qualification_risks(db: Session = Depends(get_db)) -> list[QualificationRiskSchema]:
    return [QualificationRiskSchema.from_orm(eq) for eq in list_qualification_risks(db)]
