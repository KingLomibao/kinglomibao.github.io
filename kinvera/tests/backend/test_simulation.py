"""
Tests for the assignment-extension impact simulation
(app/domain/simulation.py).

`test_john_smith_extension_scenario` rebuilds - independently of the
seed script, using the same factories as every other test here - the
exact relief-chain shape the product spec calls out by name: extending
one assignment by 14 days delays its reliever, which collides with
that reliever's own next commitment, which leaves a second site short
of its minimum staffing, with qualification constraints determining
which alternative candidates could actually cover the gap.
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
    make_staffing_requirement,
    require_qualification,
)

from app.domain.simulation import simulate_extension
from app.models.enums import AssignmentStatus


def test_simulation_does_not_mutate_original_assignment(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=30), planned_end_date=TODAY + timedelta(days=10)
    )
    original_end = assignment.planned_end_date

    simulate_extension(db, assignment.id, 14, reference_date=TODAY)

    assert assignment.planned_end_date == original_end
    db.expire(assignment)  # force a reload from the database, not Python's in-memory cache
    assert assignment.planned_end_date == original_end


def test_extension_date_is_calculated_correctly(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=30), planned_end_date=TODAY + timedelta(days=10)
    )

    result = simulate_extension(db, assignment.id, 14, reference_date=TODAY)

    assert result.original_planned_end_date == TODAY + timedelta(days=10)
    assert result.simulated_planned_end_date == TODAY + timedelta(days=24)
    assert result.extension_days == 14


def test_no_reliever_means_no_conflict(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=30), planned_end_date=TODAY + timedelta(days=10)
    )

    result = simulate_extension(db, assignment.id, 14, reference_date=TODAY)

    assert result.has_conflict is False
    assert len(result.events) == 1
    assert result.events[0].category == "extension"


def test_reliever_delay_is_detected(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    reliever = make_employee(db, role)
    target = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=30), planned_end_date=TODAY + timedelta(days=10)
    )
    make_assignment(
        db,
        reliever,
        site,
        role,
        start_date=TODAY + timedelta(days=10),
        planned_end_date=TODAY + timedelta(days=40),
        status=AssignmentStatus.PLANNED,
        relieving_assignment=target,
    )

    result = simulate_extension(db, target.id, 14, reference_date=TODAY)

    assert any(e.category == "reliever_affected" for e in result.events)


def _build_relief_chain_scenario(db, *, work_height_expiry_for_grace, work_height_expiry_for_marcus):
    """Builds the John-Smith-shaped scenario with generic names:

    `employee_a` is extended -> delays `reliever` -> who was already
    committed to relieve `employee_b` at `site_b` -> leaving `site_b`
    short of its Senior-Technician minimum, with three possible
    alternates who differ only in their qualification status.
    """
    role = make_role(db)
    site_a = make_site(db)
    site_b = make_site(db)
    work_height = make_qualification(db)
    require_qualification(db, role, work_height)
    make_staffing_requirement(db, site_b, role, minimum_required=1)

    employee_a = make_employee(db, role)
    employee_b = make_employee(db, role)
    reliever = make_employee(db, role)
    eligible_alt = make_employee(db, role)
    expired_qual_alt = make_employee(db, role)
    expiring_mid_window_alt = make_employee(db, role)

    for person, expiry in [
        (employee_a, TODAY + timedelta(days=400)),
        (employee_b, TODAY + timedelta(days=400)),
        (reliever, TODAY + timedelta(days=400)),
        (eligible_alt, TODAY + timedelta(days=400)),
        (expired_qual_alt, work_height_expiry_for_grace),
        (expiring_mid_window_alt, work_height_expiry_for_marcus),
    ]:
        grant_qualification(db, person, work_height, issue_date=TODAY - timedelta(days=200), expiry_date=expiry)

    assignment_a = make_assignment(
        db, employee_a, site_a, role, start_date=TODAY - timedelta(days=70), planned_end_date=TODAY + timedelta(days=16)
    )
    assignment_b = make_assignment(
        db,
        employee_b,
        site_b,
        role,
        start_date=TODAY - timedelta(days=100),
        planned_end_date=TODAY + timedelta(days=30),
    )
    reliever_of_a = make_assignment(
        db,
        reliever,
        site_a,
        role,
        start_date=assignment_a.planned_end_date,
        planned_end_date=assignment_a.planned_end_date + timedelta(days=14),
        status=AssignmentStatus.PLANNED,
        relieving_assignment=assignment_a,
    )
    make_assignment(
        db,
        reliever,
        site_b,
        role,
        start_date=assignment_b.planned_end_date,
        planned_end_date=assignment_b.planned_end_date + timedelta(days=45),
        status=AssignmentStatus.PLANNED,
        relieving_assignment=assignment_b,
    )

    return {
        "assignment_a": assignment_a,
        "site_b": site_b,
        "eligible_alt": eligible_alt,
        "expired_qual_alt": expired_qual_alt,
        "expiring_mid_window_alt": expiring_mid_window_alt,
        "reliever_of_a": reliever_of_a,
    }


def test_john_smith_extension_scenario(db):
    """The scenario named in the product spec: extending assignment A
    by 14 days should delay its reliever into a collision with that
    reliever's next commitment, create a staffing shortage at the
    second site, and correctly separate eligible from ineligible
    alternates based on qualification validity alone."""
    scenario = _build_relief_chain_scenario(
        db,
        work_height_expiry_for_grace=TODAY - timedelta(days=10),  # already expired
        work_height_expiry_for_marcus=TODAY + timedelta(days=40),  # expires mid-gap
    )

    result = simulate_extension(db, scenario["assignment_a"].id, 14, reference_date=TODAY)

    categories = {e.category for e in result.events}
    assert "reliever_affected" in categories
    assert "reliever_next_assignment_conflict" in categories
    assert "downstream_coverage_loss" in categories
    assert "staffing_shortage" in categories
    assert result.overall_severity == "high"

    assert len(result.staffing_impacts) == 1
    assert result.staffing_impacts[0].site_id == scenario["site_b"].id
    assert result.staffing_impacts[0].shortage > 0

    eligible_ids = {c.employee_id for c in result.eligible_alternatives}
    rejected_ids = {c.employee_id for c in result.rejected_alternatives}

    assert scenario["eligible_alt"].id in eligible_ids
    assert scenario["expired_qual_alt"].id in rejected_ids
    assert scenario["expiring_mid_window_alt"].id in rejected_ids
    # The reliever already accounted for in the main chain should not
    # also be double-counted as a fresh "alternative".
    assert scenario["reliever_of_a"].employee_id not in eligible_ids
    assert scenario["reliever_of_a"].employee_id not in rejected_ids


def test_alternatives_reuse_standard_eligibility_checks(db):
    """The reasons given for a rejected alternative in a simulation
    must be the exact same rule names the standalone eligibility
    engine produces - proving there is only one eligibility engine."""
    scenario = _build_relief_chain_scenario(
        db,
        work_height_expiry_for_grace=TODAY - timedelta(days=10),
        work_height_expiry_for_marcus=TODAY + timedelta(days=400),
    )

    result = simulate_extension(db, scenario["assignment_a"].id, 14, reference_date=TODAY)

    rejected = next(c for c in result.rejected_alternatives if c.employee_id == scenario["expired_qual_alt"].id)
    rule_names = {check.rule for check in rejected.checks}
    assert any(rule.startswith("qualification_valid:") for rule in rule_names)
    assert "role_match" in rule_names
    assert "active_employment" in rule_names
