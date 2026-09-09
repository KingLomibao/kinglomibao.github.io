from datetime import date

from pydantic import BaseModel

from app.domain.qualifications import qualification_status
from app.models import EmployeeQualification


class QualificationRiskSchema(BaseModel):
    employee_id: int
    employee_name: str
    qualification_id: int
    qualification_name: str
    expiry_date: date
    status: str

    @classmethod
    def from_orm(cls, eq: EmployeeQualification, *, reference_date: date | None = None) -> "QualificationRiskSchema":
        return cls(
            employee_id=eq.employee_id,
            employee_name=eq.employee.full_name,
            qualification_id=eq.qualification_id,
            qualification_name=eq.qualification.name,
            expiry_date=eq.expiry_date,
            status=qualification_status(eq.expiry_date, reference_date=reference_date),
        )
