"""Tests for staffing coverage logic (app/domain/staffing.py)."""

from datetime import timedelta

from factories import TODAY, make_assignment, make_employee, make_role, make_site, make_staffing_requirement

from app.domain.staffing import count_role_coverage, get_staffing_coverage, get_staffing_shortages


def test_coverage_meeting_minimum_is_not_a_shortage(db):
    role, site = make_role(db), make_site(db)
    make_staffing_requirement(db, site, role, 1)
    employee = make_employee(db, role)
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=10), planned_end_date=TODAY + timedelta(days=30)
    )

    coverage = get_staffing_coverage(db, site_id=site.id)

    assert len(coverage) == 1
    assert coverage[0].shortage == 0
    assert coverage[0].status == "meeting"
    assert coverage[0] not in get_staffing_shortages(db, site_id=site.id)


def test_coverage_below_minimum_is_a_shortage(db):
    role, site = make_role(db), make_site(db)
    make_staffing_requirement(db, site, role, 2)

    coverage = get_staffing_coverage(db, site_id=site.id)

    assert coverage[0].currently_assigned == 0
    assert coverage[0].shortage == 2
    assert coverage[0].status == "short"
    shortages = get_staffing_shortages(db, site_id=site.id)
    assert len(shortages) == 1


def test_count_role_coverage_respects_window(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    make_assignment(db, employee, site, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=10))

    inside = count_role_coverage(
        db,
        site_id=site.id,
        role_id=role.id,
        window_start=TODAY + timedelta(days=5),
        window_end=TODAY + timedelta(days=6),
    )
    outside = count_role_coverage(
        db,
        site_id=site.id,
        role_id=role.id,
        window_start=TODAY + timedelta(days=20),
        window_end=TODAY + timedelta(days=25),
    )

    assert inside == 1
    assert outside == 0


def test_count_role_coverage_excludes_named_assignments(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=10)
    )

    count = count_role_coverage(
        db,
        site_id=site.id,
        role_id=role.id,
        window_start=TODAY,
        window_end=TODAY + timedelta(days=1),
        exclude_assignment_ids=(assignment.id,),
    )

    assert count == 0
