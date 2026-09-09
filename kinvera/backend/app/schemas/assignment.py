from datetime import date

from pydantic import BaseModel

from app.models import Assignment


class AssignmentSchema(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    site_id: int
    site_name: str
    role_id: int
    role_name: str
    start_date: date
    planned_end_date: date
    actual_end_date: date | None
    status: str
    relieving_assignment_id: int | None
    notes: str | None

    @classmethod
    def from_orm_assignment(cls, assignment: Assignment) -> "AssignmentSchema":
        return cls(
            id=assignment.id,
            employee_id=assignment.employee_id,
            employee_name=assignment.employee.full_name,
            site_id=assignment.site_id,
            site_name=assignment.site.name,
            role_id=assignment.role_id,
            role_name=assignment.role.name,
            start_date=assignment.start_date,
            planned_end_date=assignment.planned_end_date,
            actual_end_date=assignment.actual_end_date,
            status=assignment.status.value,
            relieving_assignment_id=assignment.relieving_assignment_id,
            notes=assignment.notes,
        )
