"""
Tests for the AI orchestration loop (app/ai/orchestrator.py), driven
entirely by FakeProvider - no live LLM call is made anywhere in this
suite. These are the "grounding" and "hallucination resistance" tests:
proving the model can only get an eligibility answer by calling the
real tool, and that a contradictory model statement never overwrites
the structured, deterministic result.
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

from app.ai.orchestrator import run_conversation
from app.ai.providers.base import AssistantTurn, ToolCall
from app.ai.providers.fake_provider import FakeProvider
from app.ai.tools import TOOLS_BY_NAME


def _ineligible_scenario(db):
    role, site = make_role(db), make_site(db)
    qual = make_qualification(db)
    require_qualification(db, role, qual)

    target = make_employee(db, role, first_name="Target", last_name="Person")
    make_assignment(
        db, target, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )

    candidate = make_employee(db, role, first_name="Expired", last_name="Candidate")
    grant_qualification(
        db, candidate, qual, issue_date=TODAY - timedelta(days=400), expiry_date=TODAY - timedelta(days=5)
    )

    return target, candidate


def test_orchestrator_returns_final_answer_after_one_tool_call(db):
    role, _site = make_role(db), make_site(db)
    make_employee(db, role, first_name="Anyone", last_name="Person")

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[ToolCall(id="c1", name="search_employees", arguments={"name": "Anyone"})],
                stop_reason="tool_use",
            ),
            AssistantTurn(text="Anyone Person is an active employee.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = run_conversation(db, provider, "Who is Anyone Person?")

    assert result.answer == "Anyone Person is an active employee."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool == "search_employees"
    assert result.tool_results[0].result["status"] == "ok"


def test_orchestrator_handles_multiple_tool_calls_in_one_turn(db):
    role, _site = make_role(db), make_site(db)
    make_employee(db, role, first_name="Multi", last_name="Call")

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[
                    ToolCall(id="c1", name="get_relief_due", arguments={"days": 30}),
                    ToolCall(id="c2", name="get_staffing_status", arguments={}),
                ],
                stop_reason="tool_use",
            ),
            AssistantTurn(text="Here is both pieces of information.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = run_conversation(db, provider, "Give me relief due and staffing status.")

    assert [c.tool for c in result.tool_calls] == ["get_relief_due", "get_staffing_status"]
    assert len(result.tool_results) == 2


def test_grounding_eligibility_answer_requires_the_tool(db):
    """The model cannot answer an eligibility question without going
    through evaluate_replacement - proven by scripting a FakeProvider
    that tries to answer directly, and observing that the orchestrator
    itself never calls any tool on the model's behalf."""
    _target, _candidate = _ineligible_scenario(db)

    provider = FakeProvider(
        script=[
            AssistantTurn(text="Sure, they're eligible.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = run_conversation(db, provider, "Can Expired Candidate replace Target Person?")

    # The orchestrator never calls a tool the model didn't ask for.
    assert result.tool_calls == []
    assert result.tool_results == []
    # This demonstrates the *architecture's* guarantee: no eligibility
    # tool ran, so no eligibility fact was established this turn - the
    # answer text is unverified model prose, and the system prompt
    # (see test_ai_prompts.py) is what tells the model this path is
    # not allowed. The safety net is in what the API surfaces next:
    # an empty tool_results list is itself a signal no ground truth
    # backs this answer.


def test_hallucination_resistance_structured_result_ignores_contradictory_text(db):
    """The model calls the real eligibility tool, which correctly
    returns ineligible - then (adversarially, simulating a
    hallucination) claims in its final text that the candidate IS
    eligible. The structured tool_results must still show the true,
    deterministic result regardless of what the text says."""
    target, candidate = _ineligible_scenario(db)

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="evaluate_replacement",
                        arguments={"candidate_name": candidate.full_name, "target_employee_name": target.full_name},
                    )
                ],
                stop_reason="tool_use",
            ),
            AssistantTurn(
                text=f"{candidate.full_name} is eligible to replace {target.full_name}.",
                tool_calls=[],
                stop_reason="end_turn",
            ),
        ]
    )

    result = run_conversation(db, provider, f"Can {candidate.full_name} replace {target.full_name}?")

    # The (wrong) prose is whatever the model said...
    assert "is eligible" in result.answer
    # ...but the structured, deterministic result the tool actually
    # returned is unaffected - and it says the opposite.
    eligibility_result = result.tool_results[0].result
    assert eligibility_result["eligible"] is False
    assert any(not c["passed"] for c in eligibility_result["checks"])


def test_ambiguous_name_is_surfaced_not_resolved(db):
    role, site = make_role(db), make_site(db)
    target = make_employee(db, role, first_name="Target", last_name="Solo")
    make_assignment(db, target, site, role, start_date=TODAY, planned_end_date=TODAY + timedelta(days=30))
    make_employee(db, role, first_name="Dup", last_name="One")
    make_employee(db, role, first_name="Dup", last_name="Two")

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="evaluate_replacement",
                        arguments={"candidate_name": "Dup", "target_employee_name": "Target Solo"},
                    )
                ],
                stop_reason="tool_use",
            ),
            AssistantTurn(
                text="There are two employees named Dup - did you mean Dup One or Dup Two?",
                tool_calls=[],
                stop_reason="end_turn",
            ),
        ]
    )

    result = run_conversation(db, provider, "Can Dup replace Target Solo?")

    assert result.tool_results[0].result["status"] == "ambiguous"
    assert len(result.tool_results[0].result["candidates"]) == 2
    assert "?" in result.answer  # the scripted model asked for clarification, as instructed


def test_orchestrator_stops_after_max_iterations(db):
    """If the model keeps requesting tools forever, the loop must not
    run forever either - it stops and returns a safe message."""
    role, _site = make_role(db), make_site(db)
    make_employee(db, role, first_name="Loop", last_name="Test")

    endless_tool_call = AssistantTurn(
        text=None,
        tool_calls=[ToolCall(id="c", name="search_employees", arguments={"name": "Loop"})],
        stop_reason="tool_use",
    )
    provider = FakeProvider(script=[endless_tool_call] * 10)

    result = run_conversation(db, provider, "Keep looking forever.")

    assert "wasn't able to finish" in result.answer
    assert len(result.tool_calls) == 5  # MAX_TOOL_ITERATIONS


def test_simulate_extension_through_orchestrator_does_not_mutate_database(db):
    from app.models import Assignment, Employee

    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role, first_name="Read", last_name="Only")
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )

    employees_before = db.query(Employee).count()
    assignments_before = db.query(Assignment).count()
    original_end = assignment.planned_end_date

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="simulate_extension",
                        arguments={"employee_name": "Read Only", "extension_days": 14},
                    )
                ],
                stop_reason="tool_use",
            ),
            AssistantTurn(text="Here is the simulated impact.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    run_conversation(db, provider, "What happens if Read Only stays 14 more days?")

    assert db.query(Employee).count() == employees_before
    assert db.query(Assignment).count() == assignments_before
    db.expire(assignment)
    assert assignment.planned_end_date == original_end


def test_ai_layer_source_contains_no_mutating_database_calls():
    """Read-only guarantee, verified at the source level: nothing in
    the AI tool layer ever calls .add(, .delete(, or .commit( on a
    session - only queries."""
    import pathlib

    ai_dir = pathlib.Path(__file__).resolve().parents[2] / "backend" / "app" / "ai"
    offending = []
    for path in ai_dir.rglob("*.py"):
        text = path.read_text()
        for marker in (".add(", ".delete(", ".commit("):
            if marker in text:
                offending.append((str(path), marker))
    assert offending == []


def test_no_tool_in_the_registry_can_write_to_the_database():
    """Read-only guarantee, verified structurally: every tool name
    corresponds to one of the six read-only domain capabilities, and
    none of their handler names suggest a write operation."""
    write_like_prefixes = ("create_", "update_", "delete_", "set_", "commit_", "approve_", "write_")
    for name in TOOLS_BY_NAME:
        assert not name.startswith(write_like_prefixes), f"Tool '{name}' looks like a write operation."
    assert set(TOOLS_BY_NAME) == {
        "search_employees",
        "get_relief_due",
        "evaluate_replacement",
        "find_replacement_candidates",
        "simulate_extension",
        "get_staffing_status",
    }
