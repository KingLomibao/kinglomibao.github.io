"""
Tests for the AI tool layer (app/ai/tools.py, app/ai/employee_lookup.py).

No LLM is involved anywhere in this file - these are plain function
calls against a real (test) database, proving each tool correctly
wraps its underlying domain function and never re-implements the
decision itself.
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

from app.ai.employee_lookup import AmbiguousEmployeeError, EmployeeNotFoundError, resolve_employee_by_name
from app.ai.tools import execute_tool


def test_search_employees_finds_by_name(db):
    role = make_role(db)
    make_employee(db, role, first_name="Priya", last_name="Nair")

    result = execute_tool(db, "search_employees", {"name": "Priya"})

    assert result["status"] == "ok"
    assert any(e["full_name"] == "Priya Nair" for e in result["employees"])


def test_search_employees_filters_by_role_and_site(db):
    role_a = make_role(db)
    role_b = make_role(db)
    site = make_site(db)
    matching = make_employee(db, role_a, first_name="Ada", last_name="Match")
    make_assignment(db, matching, site, role_a, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))
    make_employee(db, role_b, first_name="Zoe", last_name="Nomatch")

    result = execute_tool(db, "search_employees", {"role": role_a.name, "site": site.name})

    names = [e["full_name"] for e in result["employees"]]
    assert "Ada Match" in names
    assert "Zoe Nomatch" not in names


def test_get_relief_due_tool_matches_domain_window(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role, first_name="Rhea", last_name="Soon")
    make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=10), planned_end_date=TODAY + timedelta(days=10)
    )

    result = execute_tool(db, "get_relief_due", {"days": 30})

    assert result["status"] == "ok"
    assert any(item["employee_name"] == "Rhea Soon" for item in result["items"])


def test_evaluate_replacement_tool_reflects_true_eligibility(db):
    role, site = make_role(db), make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    target = make_employee(db, role, first_name="Owen", last_name="Target")
    make_assignment(
        db, target, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )

    eligible_candidate = make_employee(db, role, first_name="Elena", last_name="Eligible")
    grant_qualification(
        db, eligible_candidate, qual, issue_date=TODAY - timedelta(days=100), expiry_date=TODAY + timedelta(days=365)
    )

    ineligible_candidate = make_employee(db, role, first_name="Ivan", last_name="Ineligible")
    grant_qualification(
        db, ineligible_candidate, qual, issue_date=TODAY - timedelta(days=400), expiry_date=TODAY - timedelta(days=5)
    )

    eligible_result = execute_tool(
        db, "evaluate_replacement", {"candidate_name": "Elena Eligible", "target_employee_name": "Owen Target"}
    )
    ineligible_result = execute_tool(
        db, "evaluate_replacement", {"candidate_name": "Ivan Ineligible", "target_employee_name": "Owen Target"}
    )

    assert eligible_result["status"] == "ok"
    assert eligible_result["eligible"] is True

    assert ineligible_result["status"] == "ok"
    assert ineligible_result["eligible"] is False
    failed_rules = [c["rule"] for c in ineligible_result["checks"] if not c["passed"]]
    assert any(rule.startswith("qualification_valid:") for rule in failed_rules)


def test_find_replacement_candidates_tool_separates_eligible_and_rejected(db):
    role, site = make_role(db), make_site(db)
    target = make_employee(db, role, first_name="Nora", last_name="Target")
    make_assignment(
        db, target, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )

    make_employee(db, role, first_name="Cara", last_name="Candidate")
    other_role = make_role(db)
    make_employee(db, other_role, first_name="Wrong", last_name="Role")

    result = execute_tool(db, "find_replacement_candidates", {"employee_name": "Nora Target"})

    assert result["status"] == "ok"
    assert result["target_employee_name"] == "Nora Target"
    eligible_names = [c["employee_name"] for c in result["eligible_candidates"]]
    assert "Cara Candidate" in eligible_names
    assert "Wrong Role" not in eligible_names  # different role entirely - not even a candidate


def test_simulate_extension_tool_is_non_destructive(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role, first_name="Sam", last_name="Extend")
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )

    result = execute_tool(db, "simulate_extension", {"employee_name": "Sam Extend", "extension_days": 14})

    assert result["status"] == "ok"
    assert result["is_destructive"] is False
    assert result["simulated_planned_end_date"] == str(TODAY + timedelta(days=34))

    db.expire(assignment)
    assert assignment.planned_end_date == TODAY + timedelta(days=20)


def test_get_staffing_status_tool_reports_shortage(db):
    role, site = make_role(db), make_site(db)
    make_staffing_requirement(db, site, role, minimum_required=2)

    result = execute_tool(db, "get_staffing_status", {"site_name": site.name, "shortages_only": True})

    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["coverage"][0]["shortage"] == 2


def test_unknown_tool_name_returns_structured_error(db):
    result = execute_tool(db, "delete_all_employees", {})
    assert result["status"] == "error"


# --- Ambiguity handling -------------------------------------------------


def test_resolve_employee_by_name_raises_not_found(db):
    try:
        resolve_employee_by_name(db, "Nobody Exists")
        raise AssertionError("expected EmployeeNotFoundError")
    except EmployeeNotFoundError:
        pass


def test_resolve_employee_by_name_raises_ambiguous_for_duplicate_full_names(db):
    role = make_role(db)
    site_a, site_b = make_site(db), make_site(db)
    first = make_employee(db, role, first_name="John", last_name="Duplicate")
    second = make_employee(db, role, first_name="John", last_name="Duplicate")
    make_assignment(db, first, site_a, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))
    make_assignment(db, second, site_b, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))

    try:
        resolve_employee_by_name(db, "John Duplicate")
        raise AssertionError("expected AmbiguousEmployeeError")
    except AmbiguousEmployeeError as err:
        assert len(err.matches) == 2
        sites = {m.site_name for m in err.matches}
        assert sites == {site_a.name, site_b.name}


def test_evaluate_replacement_tool_asks_for_clarification_on_ambiguous_name(db):
    role, site = make_role(db), make_site(db)
    target = make_employee(db, role, first_name="Target", last_name="Person")
    make_assignment(db, target, site, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))
    make_employee(db, role, first_name="Ambiguous", last_name="Name")
    make_employee(db, role, first_name="Ambiguous", last_name="Namesake")

    result = execute_tool(
        db, "evaluate_replacement", {"candidate_name": "Ambiguous", "target_employee_name": "Target Person"}
    )

    assert result["status"] == "ambiguous"
    assert len(result["candidates"]) == 2
    # The tool must not have silently picked one and evaluated them.
    assert "eligible" not in result


def test_evaluate_replacement_tool_reports_not_found(db):
    role, site = make_role(db), make_site(db)
    target = make_employee(db, role, first_name="Target", last_name="Person2")
    make_assignment(db, target, site, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))

    result = execute_tool(
        db, "evaluate_replacement", {"candidate_name": "Nobody At All", "target_employee_name": "Target Person2"}
    )

    assert result["status"] == "not_found"
    assert "eligible" not in result
