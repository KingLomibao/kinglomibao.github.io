"""Tests for relief-due logic (app/domain/relief.py)."""

from datetime import timedelta

from factories import TODAY, make_assignment, make_employee, make_role, make_site

from app.domain.relief import get_relief_due
from app.models.enums import AssignmentStatus


def test_assignment_inside_window_is_returned(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=60), planned_end_date=TODAY + timedelta(days=10)
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)

    assert any(item.employee_id == employee.id for item in items)


def test_assignment_outside_window_is_excluded(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=60), planned_end_date=TODAY + timedelta(days=90)
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)

    assert all(item.employee_id != employee.id for item in items)


def test_completed_assignment_is_excluded(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(
        db,
        employee,
        site,
        role,
        start_date=TODAY - timedelta(days=60),
        planned_end_date=TODAY + timedelta(days=10),
        status=AssignmentStatus.COMPLETED,
        actual_end_date=TODAY - timedelta(days=1),
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)

    assert all(item.employee_id != employee.id for item in items)


def test_no_reliever_is_flagged(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=60), planned_end_date=TODAY + timedelta(days=10)
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)
    item = next(i for i in items if i.employee_id == employee.id)

    assert item.reliever_status == "none"
    assert item.risk == "no_reliever"


def test_planned_reliever_is_reported(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    reliever = make_employee(db, role)
    original = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=60), planned_end_date=TODAY + timedelta(days=10)
    )
    make_assignment(
        db,
        reliever,
        site,
        role,
        start_date=TODAY + timedelta(days=10),
        planned_end_date=TODAY + timedelta(days=100),
        status=AssignmentStatus.PLANNED,
        relieving_assignment=original,
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)
    item = next(i for i in items if i.employee_id == employee.id)

    assert item.reliever_status == "planned"
    assert item.reliever_employee_id == reliever.id
    assert item.risk == "reliever_planned"


def test_days_remaining_is_calculated_correctly(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=60), planned_end_date=TODAY + timedelta(days=16)
    )

    items = get_relief_due(db, window_days=30, reference_date=TODAY)
    item = next(i for i in items if i.employee_id == employee.id)

    assert item.days_remaining == 16
