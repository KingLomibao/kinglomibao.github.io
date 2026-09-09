"""
Generates the full synthetic Kinvera dataset for Ironbridge Field
Operations, a fictional field-services company.

Run it with:

    python -m app.seed.generate_synthetic_data

It wipes and rebuilds every table, so it's always safe to re-run. A
fixed random seed makes the *random* part of the dataset reproducible;
the named scenario (see scenario.py) is fully deterministic.

The script is intentionally a single, readable, top-to-bottom
procedure - there's no need for a class hierarchy or plugin system to
generate a fixed dataset once.
"""

import itertools
import random
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Assignment,
    Employee,
    EmployeeQualification,
    Qualification,
    Role,
    RoleQualificationRequirement,
    Site,
    SiteStaffingRequirement,
    WorkforceMovement,
)
from app.models.enums import (
    AssignmentStatus,
    AvailabilityStatus,
    EmploymentStatus,
    MovementType,
)
from app.seed.extra_employees import EXTRA_RESERVED_FULL_NAMES, seed_extra_demo_employees
from app.seed.reference_data import (
    QUALIFICATIONS,
    ROLE_HEADCOUNT,
    ROLE_QUALIFICATION_REQUIREMENTS,
    ROLES,
    SITES,
    STAFFING_PROFILES,
)
from app.seed.scenario import RESERVED_FULL_NAMES, seed_named_scenario

RANDOM_SEED = 42

# (site_code, role_code) pairs that are deliberately left understaffed
# right now, independent of the John Smith simulation scenario. These
# demonstrate the Staffing Shortages dashboard feature with data that
# is short *today*, with no simulation required.
DELIBERATE_CURRENT_SHORTAGES = {
    ("RMS", "SITE_SUPV"): 0,  # demobilizing site has lost its supervisor
    ("SRTF", "INST_TECH"): 1,  # short by one instrument technician
}

# (site_code, role_code) pairs the named John Smith scenario (see
# scenario.py) already fully accounts for. Randomly assigning more
# people into these same slots would silently provide backup coverage
# that defeats the scenario's deliberate staffing-shortage outcome, so
# the general population step below leaves them alone entirely.
SCENARIO_RESERVED_SLOTS = {("MSA", "SR_FIELD_TECH")}


def reset_database(session: Session) -> None:
    """Wipe all workforce data so this script can be re-run safely."""
    tables = [
        "workforce_movements",
        "assignments",
        "employee_qualifications",
        "site_staffing_requirements",
        "role_qualification_requirements",
        "employees",
        "qualifications",
        "sites",
        "roles",
    ]
    for table in tables:
        session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    session.commit()


def create_roles(session: Session) -> dict[str, Role]:
    roles = {r["code"]: Role(code=r["code"], name=r["name"], category=r["category"]) for r in ROLES}
    session.add_all(roles.values())
    session.flush()
    return roles


def create_qualifications(session: Session) -> dict[str, Qualification]:
    quals = {
        q["code"]: Qualification(code=q["code"], name=q["name"], description=q["description"])
        for q in QUALIFICATIONS
    }
    session.add_all(quals.values())
    session.flush()
    return quals


def create_role_qualification_requirements(
    session: Session, roles: dict[str, Role], quals: dict[str, Qualification]
) -> None:
    for role_code, qual_codes in ROLE_QUALIFICATION_REQUIREMENTS.items():
        for qual_code in qual_codes:
            session.add(
                RoleQualificationRequirement(
                    role_id=roles[role_code].id,
                    qualification_id=quals[qual_code].id,
                    mandatory=True,
                )
            )
    session.flush()


def create_sites(session: Session) -> dict[str, Site]:
    sites = {s["code"]: Site(code=s["code"], name=s["name"], location=s["location"], status=s["status"]) for s in SITES}
    session.add_all(sites.values())
    session.flush()
    return sites


def create_staffing_requirements(session: Session, sites: dict[str, Site], roles: dict[str, Role]) -> None:
    for site_code, role_minimums in STAFFING_PROFILES.items():
        for role_code, minimum in role_minimums.items():
            session.add(
                SiteStaffingRequirement(
                    site_id=sites[site_code].id,
                    role_id=roles[role_code].id,
                    minimum_required=minimum,
                )
            )
    session.flush()


def generate_random_employees(
    session: Session,
    *,
    roles: dict[str, Role],
    today: date,
    employee_number_seq,
    fake: Faker,
    already_seeded_by_role: dict[str, int],
) -> dict[str, list[Employee]]:
    """Create the bulk of the workforce with randomized attributes.

    Returns employees grouped by role code, which the assignment step
    uses to fill staffing requirements per site.
    """
    employees_by_role: dict[str, list[Employee]] = {code: [] for code in roles}
    used_full_names: set[str] = set(RESERVED_FULL_NAMES) | set(EXTRA_RESERVED_FULL_NAMES)

    for role_code, target_headcount in ROLE_HEADCOUNT.items():
        remaining = target_headcount - already_seeded_by_role.get(role_code, 0)
        role = roles[role_code]
        for _ in range(remaining):
            while True:
                first_name, last_name = fake.first_name(), fake.last_name()
                full_name = f"{first_name} {last_name}"
                if full_name not in used_full_names:
                    used_full_names.add(full_name)
                    break

            # ~2% of employees are no longer with the company - present
            # in history but excluded from active workforce planning.
            terminated = random.random() < 0.02
            employment_status = EmploymentStatus.TERMINATED if terminated else EmploymentStatus.ACTIVE

            employee = Employee(
                employee_number=f"EMP-{next(employee_number_seq):04d}",
                first_name=first_name,
                last_name=last_name,
                role_id=role.id,
                employment_status=employment_status,
                availability_status=AvailabilityStatus.AVAILABLE,
                home_location=f"{fake.city()}, {fake.country()}",
                hire_date=today - timedelta(days=random.randint(60, 3000)),
                active=not terminated,
            )
            session.add(employee)
            employees_by_role[role_code].append(employee)

    session.flush()
    return employees_by_role


def grant_qualifications_for_employee(
    session: Session,
    employee: Employee,
    role_code: str,
    quals: dict[str, Qualification],
    today: date,
) -> None:
    """Issue each mandatory qualification for the employee's role.

    Most employees are fully and validly qualified (realistic - that's
    the normal case). A deliberate minority are seeded with expired,
    soon-to-expire, or entirely missing qualifications so the
    Qualification Risks dashboard and the eligibility engine's
    qualification checks have real cases to surface.
    """
    if employee.employment_status == EmploymentStatus.TERMINATED:
        return

    for qual_code in ROLE_QUALIFICATION_REQUIREMENTS[role_code]:
        roll = random.random()
        if roll < 0.05:
            # Missing entirely - a hard eligibility failure for this role.
            continue
        issue_date = today - timedelta(days=random.randint(30, 900))
        if roll < 0.10:
            expiry_date = today - timedelta(days=random.randint(1, 60))  # already expired
        elif roll < 0.22:
            expiry_date = today + timedelta(days=random.randint(1, 30))  # expiring soon
        else:
            expiry_date = today + timedelta(days=random.randint(120, 900))  # comfortably valid

        session.add(
            EmployeeQualification(
                employee_id=employee.id,
                qualification_id=quals[qual_code].id,
                issue_date=issue_date,
                expiry_date=expiry_date,
            )
        )


def build_assignments(
    session: Session,
    *,
    sites: dict[str, Site],
    roles: dict[str, Role],
    employees_by_role: dict[str, list[Employee]],
    today: date,
) -> None:
    """Deploy a realistic share of the workforce to sites right now,
    plan some future relief, and leave the rest on the bench
    (available / on leave / unavailable) so there is a real pool of
    candidates for replacement searches.
    """
    role_pools = {code: list(emps) for code, emps in employees_by_role.items()}
    for pool in role_pools.values():
        random.shuffle(pool)

    active_assignments: list[Assignment] = []

    for site_code, role_minimums in STAFFING_PROFILES.items():
        site = sites[site_code]
        for role_code, minimum in role_minimums.items():
            if (site_code, role_code) in SCENARIO_RESERVED_SLOTS:
                continue

            shortage = DELIBERATE_CURRENT_SHORTAGES.get((site_code, role_code))
            headcount = shortage if shortage is not None else minimum + (1 if random.random() < 0.35 else 0)

            pool = role_pools[role_code]
            for _ in range(headcount):
                if not pool:
                    break
                employee = pool.pop()
                if employee.employment_status == EmploymentStatus.TERMINATED:
                    continue

                start_date = today - timedelta(days=random.randint(5, 180))
                planned_end_date = today + timedelta(days=random.randint(3, 100))

                assignment = Assignment(
                    employee_id=employee.id,
                    site_id=site.id,
                    role_id=roles[role_code].id,
                    start_date=start_date,
                    planned_end_date=planned_end_date,
                    status=AssignmentStatus.ACTIVE,
                )
                employee.availability_status = AvailabilityStatus.ASSIGNED
                session.add(assignment)
                session.flush()
                active_assignments.append(assignment)

                session.add(
                    WorkforceMovement(
                        employee_id=employee.id,
                        assignment_id=assignment.id,
                        movement_type=random.choice([MovementType.MOBILIZATION, MovementType.ROTATION_IN]),
                        movement_date=start_date,
                        to_site_id=site.id,
                    )
                )

    # For roughly 60% of active assignments ending within 45 days,
    # line up a planned reliever drawn from that role's bench - the
    # rest are deliberately left with no reliever assigned yet, which
    # the Relief Due view should flag as a risk.
    for assignment in active_assignments:
        days_remaining = (assignment.planned_end_date - today).days
        if days_remaining > 45 or random.random() >= 0.6:
            continue

        role_code = next(code for code, r in roles.items() if r.id == assignment.role_id)
        bench = [
            e
            for e in role_pools[role_code]
            if e.availability_status == AvailabilityStatus.AVAILABLE
            and e.employment_status == EmploymentStatus.ACTIVE
        ]
        if not bench:
            continue
        reliever = random.choice(bench)
        role_pools[role_code].remove(reliever)

        relief_assignment = Assignment(
            employee_id=reliever.id,
            site_id=assignment.site_id,
            role_id=assignment.role_id,
            start_date=assignment.planned_end_date,
            planned_end_date=assignment.planned_end_date + timedelta(days=random.randint(30, 120)),
            status=AssignmentStatus.PLANNED,
            relieving_assignment_id=assignment.id,
        )
        session.add(relief_assignment)
        session.flush()
        session.add(
            WorkforceMovement(
                employee_id=reliever.id,
                assignment_id=relief_assignment.id,
                movement_type=MovementType.RELIEF_IN,
                movement_date=relief_assignment.start_date,
                to_site_id=assignment.site_id,
            )
        )

    # A modest set of completed historical assignments, so employee
    # detail pages have "recent movement" to show, not just the future.
    all_employees = [e for pool in employees_by_role.values() for e in pool]
    for employee in random.sample(all_employees, k=min(60, len(all_employees))):
        role_code = next(code for code, r in roles.items() if r.id == employee.role_id)
        site = random.choice(list(sites.values()))
        start_date = today - timedelta(days=random.randint(400, 900))
        actual_end_date = start_date + timedelta(days=random.randint(60, 240))
        if actual_end_date >= today:
            continue

        past_assignment = Assignment(
            employee_id=employee.id,
            site_id=site.id,
            role_id=roles[role_code].id,
            start_date=start_date,
            planned_end_date=actual_end_date,
            actual_end_date=actual_end_date,
            status=AssignmentStatus.COMPLETED,
        )
        session.add(past_assignment)
        session.flush()
        session.add_all(
            [
                WorkforceMovement(
                    employee_id=employee.id,
                    assignment_id=past_assignment.id,
                    movement_type=MovementType.MOBILIZATION,
                    movement_date=start_date,
                    to_site_id=site.id,
                ),
                WorkforceMovement(
                    employee_id=employee.id,
                    assignment_id=past_assignment.id,
                    movement_type=MovementType.DEMOBILIZATION,
                    movement_date=actual_end_date,
                    from_site_id=site.id,
                ),
            ]
        )

    # Employees left on the bench get a plausible reason for it.
    for pool in role_pools.values():
        for employee in pool:
            if employee.employment_status == EmploymentStatus.TERMINATED:
                employee.availability_status = AvailabilityStatus.UNAVAILABLE
                continue
            employee.availability_status = random.choices(
                [
                    AvailabilityStatus.AVAILABLE,
                    AvailabilityStatus.ON_LEAVE,
                    AvailabilityStatus.UNAVAILABLE,
                ],
                weights=[0.55, 0.25, 0.20],
            )[0]


def main() -> None:
    random.seed(RANDOM_SEED)
    fake = Faker()
    Faker.seed(RANDOM_SEED)
    today = date.today()
    employee_number_seq = itertools.count(1)

    session = SessionLocal()
    try:
        reset_database(session)

        roles = create_roles(session)
        quals = create_qualifications(session)
        create_role_qualification_requirements(session, roles, quals)
        sites = create_sites(session)
        create_staffing_requirements(session, sites, roles)

        seed_named_scenario(
            session,
            roles=roles,
            sites=sites,
            qualifications=quals,
            today=today,
            employee_number_seq=employee_number_seq,
        )
        session.flush()

        seed_extra_demo_employees(
            session,
            roles=roles,
            sites=sites,
            qualifications=quals,
            today=today,
            employee_number_seq=employee_number_seq,
        )
        session.flush()

        employees_by_role = generate_random_employees(
            session,
            roles=roles,
            today=today,
            employee_number_seq=employee_number_seq,
            fake=fake,
            already_seeded_by_role={"SR_FIELD_TECH": 6},  # the 6 named scenario employees
        )

        for role_code, employees in employees_by_role.items():
            for employee in employees:
                grant_qualifications_for_employee(session, employee, role_code, quals, today)
        session.flush()

        build_assignments(session, sites=sites, roles=roles, employees_by_role=employees_by_role, today=today)

        session.commit()

        total_employees = session.query(Employee).count()
        total_assignments = session.query(Assignment).count()
        print(f"Seeded {total_employees} employees across {len(sites)} sites.")
        print(f"Seeded {total_assignments} assignments (active, planned, and completed).")
        print(f"Reference date used for all relative dates: {today.isoformat()}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
