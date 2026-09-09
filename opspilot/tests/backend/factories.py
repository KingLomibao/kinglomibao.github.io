"""
Minimal, explicit test-data builders.

Rather than reusing the synthetic-data generator (which is randomized
and tuned for a realistic demo, not for pinpointing one rule), each
test builds exactly the handful of records it needs via these small
factory functions. That keeps every test's setup readable top-to-bottom
and independent of the seed script's random choices.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    Employee,
    EmployeeQualification,
    Qualification,
    Role,
    RoleQualificationRequirement,
    Site,
    SiteStaffingRequirement,
)
from app.models.enums import (
    AssignmentStatus,
    AvailabilityStatus,
    EmploymentStatus,
    RoleCategory,
    SiteStatus,
)

TODAY = date(2026, 9, 9)

_counter = iter(range(1, 1_000_000))


def _unique(prefix: str) -> str:
    return f"{prefix}{next(_counter)}"


def make_role(db: Session, *, category: RoleCategory = RoleCategory.TECHNICAL) -> Role:
    role = Role(code=_unique("ROLE"), name=_unique("Role "), category=category)
    db.add(role)
    db.flush()
    return role


def make_site(db: Session, *, status: SiteStatus = SiteStatus.ACTIVE) -> Site:
    site = Site(code=_unique("SITE"), name=_unique("Site "), location="Test Location", status=status)
    db.add(site)
    db.flush()
    return site


def make_qualification(db: Session) -> Qualification:
    qual = Qualification(code=_unique("QUAL"), name=_unique("Qualification "))
    db.add(qual)
    db.flush()
    return qual


def require_qualification(db: Session, role: Role, qualification: Qualification, *, mandatory: bool = True) -> None:
    db.add(RoleQualificationRequirement(role_id=role.id, qualification_id=qualification.id, mandatory=mandatory))
    db.flush()


def make_staffing_requirement(db: Session, site: Site, role: Role, minimum_required: int) -> SiteStaffingRequirement:
    req = SiteStaffingRequirement(site_id=site.id, role_id=role.id, minimum_required=minimum_required)
    db.add(req)
    db.flush()
    return req


def make_employee(
    db: Session,
    role: Role,
    *,
    active: bool = True,
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE,
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
) -> Employee:
    employee = Employee(
        employee_number=_unique("EMP"),
        first_name=_unique("First"),
        last_name=_unique("Last"),
        role_id=role.id,
        employment_status=employment_status,
        availability_status=availability_status,
        hire_date=TODAY - timedelta(days=500),
        active=active,
    )
    db.add(employee)
    db.flush()
    return employee


def grant_qualification(
    db: Session, employee: Employee, qualification: Qualification, *, issue_date: date, expiry_date: date
) -> EmployeeQualification:
    eq = EmployeeQualification(
        employee_id=employee.id,
        qualification_id=qualification.id,
        issue_date=issue_date,
        expiry_date=expiry_date,
    )
    db.add(eq)
    db.flush()
    return eq


def make_assignment(
    db: Session,
    employee: Employee,
    site: Site,
    role: Role,
    *,
    start_date: date,
    planned_end_date: date,
    status: AssignmentStatus = AssignmentStatus.ACTIVE,
    relieving_assignment: Assignment | None = None,
    actual_end_date: date | None = None,
) -> Assignment:
    assignment = Assignment(
        employee_id=employee.id,
        site_id=site.id,
        role_id=role.id,
        start_date=start_date,
        planned_end_date=planned_end_date,
        actual_end_date=actual_end_date,
        status=status,
        relieving_assignment_id=relieving_assignment.id if relieving_assignment else None,
    )
    db.add(assignment)
    db.flush()
    return assignment
