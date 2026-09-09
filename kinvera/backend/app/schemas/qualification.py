from datetime import date

from pydantic import BaseModel

from app.domain.qualifications import qualification_status
from app.models import EmployeeQualification, Qualification


class QualificationSchema(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None

    @classmethod
    def from_orm_qualification(cls, qualification: Qualification) -> "QualificationSchema":
        return cls(
            id=qualification.id, code=qualification.code, name=qualification.name, description=qualification.description
        )


class EmployeeQualificationSchema(BaseModel):
    id: int
    qualification: QualificationSchema
    issue_date: date
    expiry_date: date
    status: str

    @classmethod
    def from_orm(
        cls, eq: EmployeeQualification, *, reference_date: date | None = None
    ) -> "EmployeeQualificationSchema":
        return cls(
            id=eq.id,
            qualification=QualificationSchema.from_orm_qualification(eq.qualification),
            issue_date=eq.issue_date,
            expiry_date=eq.expiry_date,
            status=qualification_status(eq.expiry_date, reference_date=reference_date),
        )
