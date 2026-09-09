"""
The hand-crafted "John Smith" scenario.

Everything else in the synthetic dataset is randomly generated, but
this module builds a small, fully deterministic slice of data by hand
so the portfolio demo always has a reliable story to walk through:

  1. John Smith is currently assigned at Northfield Compression Station
     and is due for relief soon (within the default 30-day window).
  2. Ahmed Rahman is already planned to relieve him.
  3. Ahmed is *also* already committed to relieve Priya Nair at a
     second site (Meridian Solar Array) immediately after his stint
     relieving John ends.
  4. Extending John by 14 days pushes Ahmed's relief of John later,
     which collides with Ahmed's already-scheduled relief of Priya -
     he cannot be in two places at once. That, in turn, leaves
     Meridian Solar Array short-staffed for Senior Field Technicians
     until someone else covers the gap.
  5. A few other Senior Field Technicians exist specifically to make
     "who else could cover this?" interesting: one is genuinely
     eligible (Diego Alvarez), two are not (an expired and a
     soon-to-expire Working at Height certification), demonstrating
     that qualification constraints - not just availability - limit
     the alternatives.

This is the scenario documented in detail in
docs/business-rules.md under "Seeded demonstration scenario".
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    Employee,
    EmployeeQualification,
    Qualification,
    Role,
    Site,
    WorkforceMovement,
)
from app.models.enums import (
    AssignmentStatus,
    AvailabilityStatus,
    EmploymentStatus,
    MovementType,
)

RESERVED_FULL_NAMES = {
    "John Smith",
    "Ahmed Rahman",
    "Priya Nair",
    "Diego Alvarez",
    "Grace Kim",
    "Marcus Webb",
}


def seed_named_scenario(
    session: Session,
    *,
    roles: dict[str, Role],
    sites: dict[str, Site],
    qualifications: dict[str, Qualification],
    today: date,
    employee_number_seq,
) -> None:
    sr_field_tech = roles["SR_FIELD_TECH"]
    nfcs = sites["NFCS"]
    msa = sites["MSA"]

    def make_employee(first_name: str, last_name: str, home_location: str) -> Employee:
        employee = Employee(
            employee_number=f"EMP-{next(employee_number_seq):04d}",
            first_name=first_name,
            last_name=last_name,
            role_id=sr_field_tech.id,
            employment_status=EmploymentStatus.ACTIVE,
            availability_status=AvailabilityStatus.ASSIGNED,
            home_location=home_location,
            hire_date=today - timedelta(days=900),
            active=True,
        )
        session.add(employee)
        session.flush()
        return employee

    def grant_qualifications(employee: Employee, *, work_height_expiry: date) -> None:
        """Give this employee the quals a Senior Field Technician needs.

        `work_height_expiry` is the one date every candidate in this
        scenario differs on - it's what makes some of them eligible
        replacements and others not.
        """
        session.add_all(
            [
                EmployeeQualification(
                    employee_id=employee.id,
                    qualification_id=qualifications["SITE_INDUCTION"].id,
                    issue_date=today - timedelta(days=800),
                    expiry_date=today + timedelta(days=700),
                ),
                EmployeeQualification(
                    employee_id=employee.id,
                    qualification_id=qualifications["FIRST_AID"].id,
                    issue_date=today - timedelta(days=500),
                    expiry_date=today + timedelta(days=200),
                ),
                EmployeeQualification(
                    employee_id=employee.id,
                    qualification_id=qualifications["WORK_HEIGHT"].id,
                    issue_date=today - timedelta(days=600),
                    expiry_date=work_height_expiry,
                ),
            ]
        )

    # --- John Smith: currently assigned, relief already planned -----
    john = make_employee("John", "Smith", "Calgary, Canada")
    grant_qualifications(john, work_height_expiry=today + timedelta(days=400))

    john_assignment = Assignment(
        employee_id=john.id,
        site_id=nfcs.id,
        role_id=sr_field_tech.id,
        start_date=today - timedelta(days=70),
        planned_end_date=today + timedelta(days=16),
        status=AssignmentStatus.ACTIVE,
        notes="Seeded scenario: relief already planned; try extending by 14 days.",
    )
    session.add(john_assignment)
    session.flush()
    session.add(
        WorkforceMovement(
            employee_id=john.id,
            assignment_id=john_assignment.id,
            movement_type=MovementType.MOBILIZATION,
            movement_date=john_assignment.start_date,
            to_site_id=nfcs.id,
        )
    )

    # --- Priya Nair: currently assigned at the second site ----------
    priya = make_employee("Priya", "Nair", "Reno, USA")
    grant_qualifications(priya, work_height_expiry=today + timedelta(days=500))

    priya_assignment = Assignment(
        employee_id=priya.id,
        site_id=msa.id,
        role_id=sr_field_tech.id,
        start_date=today - timedelta(days=100),
        planned_end_date=today + timedelta(days=30),
        status=AssignmentStatus.ACTIVE,
        notes="Seeded scenario: Ahmed Rahman is already scheduled to relieve her.",
    )
    session.add(priya_assignment)
    session.flush()
    session.add(
        WorkforceMovement(
            employee_id=priya.id,
            assignment_id=priya_assignment.id,
            movement_type=MovementType.MOBILIZATION,
            movement_date=priya_assignment.start_date,
            to_site_id=msa.id,
        )
    )

    # --- Ahmed Rahman: currently available, double-booked ahead -----
    ahmed = make_employee("Ahmed", "Rahman", "Houston, USA")
    ahmed.availability_status = AvailabilityStatus.AVAILABLE
    grant_qualifications(ahmed, work_height_expiry=today + timedelta(days=600))

    # Planned relief #1: relieve John at Northfield the day John's
    # current assignment is due to end.
    ahmed_relief_of_john = Assignment(
        employee_id=ahmed.id,
        site_id=nfcs.id,
        role_id=sr_field_tech.id,
        start_date=john_assignment.planned_end_date,
        planned_end_date=john_assignment.planned_end_date + timedelta(days=14),
        status=AssignmentStatus.PLANNED,
        relieving_assignment_id=john_assignment.id,
        notes="Seeded scenario: planned reliever for John Smith.",
    )
    session.add(ahmed_relief_of_john)
    session.flush()
    session.add(
        WorkforceMovement(
            employee_id=ahmed.id,
            assignment_id=ahmed_relief_of_john.id,
            movement_type=MovementType.RELIEF_IN,
            movement_date=ahmed_relief_of_john.start_date,
            to_site_id=nfcs.id,
        )
    )

    # Planned relief #2: immediately afterwards, relieve Priya at
    # Meridian Solar Array. This is the commitment that a 14-day
    # extension of John's assignment collides with.
    ahmed_relief_of_priya = Assignment(
        employee_id=ahmed.id,
        site_id=msa.id,
        role_id=sr_field_tech.id,
        start_date=priya_assignment.planned_end_date,
        planned_end_date=priya_assignment.planned_end_date + timedelta(days=45),
        status=AssignmentStatus.PLANNED,
        relieving_assignment_id=priya_assignment.id,
        notes="Seeded scenario: already committed here right after relieving John Smith.",
    )
    session.add(ahmed_relief_of_priya)
    session.flush()
    session.add(
        WorkforceMovement(
            employee_id=ahmed.id,
            assignment_id=ahmed_relief_of_priya.id,
            movement_type=MovementType.RELIEF_IN,
            movement_date=ahmed_relief_of_priya.start_date,
            to_site_id=msa.id,
        )
    )

    # --- Alternative candidates for the demo's "who else could cover
    #     this?" step. All three are Senior Field Technicians who are
    #     currently available; only Diego is actually eligible.
    diego = make_employee("Diego", "Alvarez", "Portland, USA")
    diego.availability_status = AvailabilityStatus.AVAILABLE
    grant_qualifications(diego, work_height_expiry=today + timedelta(days=365))

    grace = make_employee("Grace", "Kim", "Denver, USA")
    grace.availability_status = AvailabilityStatus.AVAILABLE
    # Working at Height already expired - fails qualification_validity outright.
    grant_qualifications(grace, work_height_expiry=today - timedelta(days=10))

    marcus = make_employee("Marcus", "Webb", "Austin, USA")
    marcus.availability_status = AvailabilityStatus.AVAILABLE
    # Valid today, but expires partway through the relief window that
    # would open up at Meridian Solar Array - fails "valid through end date".
    marcus.hire_date = today - timedelta(days=900)
    grant_qualifications(marcus, work_height_expiry=priya_assignment.planned_end_date + timedelta(days=10))
