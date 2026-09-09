"""
Tests for the replacement-eligibility engine (app/domain/eligibility.py).

Each test builds the smallest possible scenario that isolates one
rule, so a failure points straight at the rule that broke.
"""

from datetime import timedelta

from factories import (
    TODAY,
    grant_qualification,
    make_assignment,
    make_employee,
    make_qualification,
    make_role,
    make_site,
    require_qualification,
)

from app.domain.eligibility import evaluate_replacement_eligibility
from app.models.enums import AssignmentStatus, AvailabilityStatus, EmploymentStatus, RoleCategory

WINDOW_START = TODAY
WINDOW_END = TODAY + timedelta(days=30)


def _fully_qualified_employee(db, role, quals, **kwargs):
    employee = make_employee(db, role, **kwargs)
    for qual in quals:
        grant_qualification(
            db, employee, qual, issue_date=TODAY - timedelta(days=100), expiry_date=TODAY + timedelta(days=365)
        )
    return employee


def test_valid_replacement_is_eligible(db):
    role = make_role(db)
    site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(db, role, [qual])

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is True
    assert all(check.passed for check in result.checks)


def test_wrong_role_is_ineligible(db):
    required_role = make_role(db)
    other_role = make_role(db)
    site = make_site(db)

    candidate = make_employee(db, other_role)

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=required_role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    role_check = next(c for c in result.checks if c.rule == "role_match")
    assert role_check.passed is False


def test_inactive_employee_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(
        db, role, [qual], active=False, employment_status=EmploymentStatus.TERMINATED
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == "active_employment")
    assert check.passed is False


def test_unavailable_employee_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(db, role, [qual], availability_status=AvailabilityStatus.UNAVAILABLE)

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == "availability_status")
    assert check.passed is False


def test_expired_qualification_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = make_employee(db, role)
    grant_qualification(
        db, candidate, qual, issue_date=TODAY - timedelta(days=400), expiry_date=TODAY - timedelta(days=5)
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == f"qualification_valid:{qual.code}")
    assert check.passed is False
    assert "expires" in check.reason


def test_qualification_expiring_during_assignment_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = make_employee(db, role)
    # Valid on day one of the assignment, but expires before it ends.
    grant_qualification(
        db, candidate, qual, issue_date=TODAY - timedelta(days=100), expiry_date=WINDOW_START + timedelta(days=10)
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == f"qualification_valid:{qual.code}")
    assert check.passed is False


def test_overlapping_active_assignment_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    other_site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(db, role, [qual])
    make_assignment(
        db,
        candidate,
        other_site,
        role,
        start_date=WINDOW_START - timedelta(days=10),
        planned_end_date=WINDOW_START + timedelta(days=15),
        status=AssignmentStatus.ACTIVE,
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == "no_overlapping_assignment")
    assert check.passed is False


def test_future_commitment_conflict_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    other_site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(db, role, [qual])
    make_assignment(
        db,
        candidate,
        other_site,
        role,
        start_date=WINDOW_END - timedelta(days=5),
        planned_end_date=WINDOW_END + timedelta(days=60),
        status=AssignmentStatus.PLANNED,
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == "no_conflicting_future_commitment")
    assert check.passed is False


def test_rest_rotation_violation_is_ineligible(db):
    role = make_role(db)
    site = make_site(db)
    other_site = make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    candidate = _fully_qualified_employee(db, role, [qual])
    # Ends the same day the new window starts - zero rest days.
    make_assignment(
        db,
        candidate,
        other_site,
        role,
        start_date=WINDOW_START - timedelta(days=90),
        planned_end_date=WINDOW_START,
        status=AssignmentStatus.COMPLETED,
        actual_end_date=WINDOW_START,
    )

    result = evaluate_replacement_eligibility(
        db, candidate, role_id=role.id, site_id=site.id, window_start=WINDOW_START, window_end=WINDOW_END
    )

    assert result.eligible is False
    check = next(c for c in result.checks if c.rule == "rest_rotation_rule")
    assert check.passed is False


def test_role_category_is_available_for_future_rules(db):
    """Sanity check that RoleCategory is wired up - not a business rule
    itself, just confirms the enum plumbing used by other tests."""
    role = make_role(db, category=RoleCategory.SUPERVISORY)
    assert role.category == RoleCategory.SUPERVISORY
