"""Tests for replacement search (app/domain/replacement.py)."""

from datetime import timedelta

import pytest
from factories import TODAY, make_assignment, make_employee, make_role, make_site

from app.domain.replacement import AssignmentNotFoundError, find_replacement_candidates


def test_target_employee_is_excluded_from_candidates(db):
    role, site = make_role(db), make_site(db)
    target_employee = make_employee(db, role)
    assignment = make_assignment(
        db,
        target_employee,
        site,
        role,
        start_date=TODAY - timedelta(days=10),
        planned_end_date=TODAY + timedelta(days=20),
    )

    result = find_replacement_candidates(db, assignment.id, reference_date=TODAY)

    all_candidate_ids = {c.employee_id for c in result.eligible_candidates + result.rejected_candidates}
    assert target_employee.id not in all_candidate_ids


def test_eligible_candidate_is_found(db):
    role, site = make_role(db), make_site(db)
    target_employee = make_employee(db, role)
    candidate = make_employee(db, role)
    assignment = make_assignment(
        db,
        target_employee,
        site,
        role,
        start_date=TODAY - timedelta(days=10),
        planned_end_date=TODAY + timedelta(days=20),
    )

    result = find_replacement_candidates(db, assignment.id, reference_date=TODAY)

    assert candidate.id in {c.employee_id for c in result.eligible_candidates}


def test_missing_assignment_raises(db):
    with pytest.raises(AssignmentNotFoundError):
        find_replacement_candidates(db, 999_999, reference_date=TODAY)
