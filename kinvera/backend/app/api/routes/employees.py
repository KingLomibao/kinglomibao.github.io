from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.schemas.employee import EmployeeDetailSchema, EmployeeSummarySchema

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeSummarySchema])
def list_employees(
    role_id: int | None = None,
    availability_status: str | None = None,
    search: str | None = Query(
        default=None, description="Matches first name, last name, or full name, case-insensitively."
    ),
    db: Session = Depends(get_db),
) -> list[EmployeeSummarySchema]:
    query = db.query(Employee)
    if role_id is not None:
        query = query.filter(Employee.role_id == role_id)
    if availability_status is not None:
        query = query.filter(Employee.availability_status == availability_status)
    if search:
        pattern = f"%{search}%"
        full_name = func.concat(Employee.first_name, " ", Employee.last_name)
        query = query.filter(
            or_(Employee.first_name.ilike(pattern), Employee.last_name.ilike(pattern), full_name.ilike(pattern))
        )

    employees = query.order_by(Employee.last_name, Employee.first_name).all()
    return [EmployeeSummarySchema.from_orm_employee(e) for e in employees]


@router.get("/{employee_id}", response_model=EmployeeDetailSchema)
def read_employee(employee_id: int, db: Session = Depends(get_db)) -> EmployeeDetailSchema:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found.")
    return EmployeeDetailSchema.from_orm_employee(employee)
