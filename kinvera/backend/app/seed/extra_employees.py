"""
A small set of additional, hand-named demo employees.

Unlike `scenario.py`, these employees are not part of any deterministic
business-rule demonstration - they're ordinary, fully-qualified,
currently-assigned staff added purely to broaden the synthetic roster
with some hand-picked names. They deliberately avoid every site/role
pairing the John Smith scenario (`scenario.py`) or the deliberate
staffing shortages (`generate_synthetic_data.py`) depend on, so they
have no effect on any existing demonstration or business-rule result.

All names and data here are entirely fictional, for portfolio/demo
purposes only.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Assignment, Employee, EmployeeQualification, Qualification, Role, Site, WorkforceMovement
from app.models.enums import AssignmentStatus, AvailabilityStatus, EmploymentStatus, MovementType
from app.seed.reference_data import ROLE_QUALIFICATION_REQUIREMENTS

# (first_name, last_name, role_code, site_code, home_location)
EXTRA_DEMO_EMPLOYEES = [
    ("Martins", "Guriz", "FIELD_TECH", "NFCS", "Riga, Latvia"),
    ("King The Greatest of them All", "Baolomi", "SITE_SUPV", "SRTF", "Manila, Philippines"),
    ("Firosh", "CM", "ELEC_TECH", "CWF", "Kochi, India"),
    ("Myron", "Belo", "INST_TECH", "VDC", "Athens, Greece"),
    ("Nino", "Abile", "MECH_TECH", "RWTF", "Milan, Italy"),
]

EXTRA_RESERVED_FULL_NAMES = {f"{first} {last}" for first, last, *_ in EXTRA_DEMO_EMPLOYEES}


def seed_extra_demo_employees(
    session: Session,
    *,
    roles: dict[str, Role],
    sites: dict[str, Site],
    qualifications: dict[str, Qualification],
    today: date,
    employee_number_seq,
) -> None:
    for first_name, last_name, role_code, site_code, home_location in EXTRA_DEMO_EMPLOYEES:
        role = roles[role_code]
        site = sites[site_code]

        employee = Employee(
            employee_number=f"EMP-{next(employee_number_seq):04d}",
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            employment_status=EmploymentStatus.ACTIVE,
            availability_status=AvailabilityStatus.ASSIGNED,
            home_location=home_location,
            hire_date=today - timedelta(days=500),
            active=True,
        )
        session.add(employee)
        session.flush()

        session.add_all(
            EmployeeQualification(
                employee_id=employee.id,
                qualification_id=qualifications[qual_code].id,
                issue_date=today - timedelta(days=400),
                expiry_date=today + timedelta(days=400),
            )
            for qual_code in ROLE_QUALIFICATION_REQUIREMENTS[role_code]
        )

        assignment = Assignment(
            employee_id=employee.id,
            site_id=site.id,
            role_id=role.id,
            start_date=today - timedelta(days=60),
            planned_end_date=today + timedelta(days=120),
            status=AssignmentStatus.ACTIVE,
            notes="Added to the demo roster as a normal, fully-qualified employee.",
        )
        session.add(assignment)
        session.flush()

        session.add(
            WorkforceMovement(
                employee_id=employee.id,
                assignment_id=assignment.id,
                movement_type=MovementType.MOBILIZATION,
                movement_date=assignment.start_date,
                to_site_id=site.id,
            )
        )
