from datetime import date

from pydantic import BaseModel

from app.domain.employee_view import assignment_history, current_assignment, next_planned_assignment
from app.models import Employee
from app.schemas.assignment import AssignmentSchema
from app.schemas.qualification import EmployeeQualificationSchema
from app.schemas.role import RoleSchema


class EmployeeSummarySchema(BaseModel):
    id: int
    employee_number: str
    full_name: str
    role: RoleSchema
    employment_status: str
    availability_status: str
    home_location: str | None
    active: bool
    current_assignment: AssignmentSchema | None

    @classmethod
    def from_orm_employee(cls, employee: Employee) -> "EmployeeSummarySchema":
        current = current_assignment(employee)
        return cls(
            id=employee.id,
            employee_number=employee.employee_number,
            full_name=employee.full_name,
            role=RoleSchema.from_orm_role(employee.role),
            employment_status=employee.employment_status.value,
            availability_status=employee.availability_status.value,
            home_location=employee.home_location,
            active=employee.active,
            current_assignment=AssignmentSchema.from_orm_assignment(current) if current else None,
        )


class EmployeeDetailSchema(EmployeeSummarySchema):
    hire_date: date
    next_assignment: AssignmentSchema | None
    qualifications: list[EmployeeQualificationSchema]
    assignment_history: list[AssignmentSchema]

    @classmethod
    def from_orm_employee(cls, employee: Employee, *, reference_date: date | None = None) -> "EmployeeDetailSchema":
        summary = EmployeeSummarySchema.from_orm_employee(employee)
        next_assignment = next_planned_assignment(employee)
        return cls(
            **summary.model_dump(),
            hire_date=employee.hire_date,
            next_assignment=AssignmentSchema.from_orm_assignment(next_assignment) if next_assignment else None,
            qualifications=[
                EmployeeQualificationSchema.from_orm(eq, reference_date=reference_date)
                for eq in employee.qualifications
            ],
            assignment_history=[AssignmentSchema.from_orm_assignment(a) for a in assignment_history(employee)],
        )
