"""
API-level tests for POST /api/assistant/chat, with the LLM provider
dependency overridden to FakeProvider - no live API call is made.
"""

from datetime import timedelta

from factories import TODAY, make_assignment, make_employee, make_role, make_site
from fastapi.testclient import TestClient

from app.ai.providers.base import AssistantTurn, ToolCall
from app.ai.providers.fake_provider import FakeProvider
from app.api.routes.assistant import require_llm_provider
from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models.enums import AssignmentStatus


def make_client(db, provider: FakeProvider) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_llm_provider] = lambda: provider
    return TestClient(app)


def test_chat_endpoint_returns_answer_tool_calls_and_sources(db):
    role, _site = make_role(db), make_site(db)
    make_employee(db, role, first_name="Api", last_name="Test")

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[ToolCall(id="c1", name="search_employees", arguments={"name": "Api"})],
                stop_reason="tool_use",
            ),
            AssistantTurn(text="Api Test is an active employee.", tool_calls=[], stop_reason="end_turn"),
        ]
    )
    client = make_client(db, provider)

    response = client.post("/api/assistant/chat", json={"message": "Who is Api Test?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Api Test is an active employee."
    assert body["sources"] == ["search_employees"]
    assert body["tool_calls"][0]["tool"] == "search_employees"
    assert body["tool_results"][0]["result"]["status"] == "ok"


def test_chat_endpoint_flagship_extension_scenario(db):
    """The API-level equivalent of the seeded John Smith +14-day
    scenario, built via factories so it doesn't depend on the seed
    script, proving the assistant endpoint surfaces the exact same
    deterministic chain the domain layer produces."""
    role = make_role(db)
    site_a, site_b = make_site(db), make_site(db)

    employee_a = make_employee(db, role, first_name="Chain", last_name="A")
    employee_b = make_employee(db, role, first_name="Chain", last_name="B")
    reliever = make_employee(db, role, first_name="Chain", last_name="Reliever")

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
    make_assignment(
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

    provider = FakeProvider(
        script=[
            AssistantTurn(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="simulate_extension",
                        arguments={"employee_name": "Chain A", "extension_days": 14},
                    )
                ],
                stop_reason="tool_use",
            ),
            AssistantTurn(
                text="Extending Chain A by 14 days delays the reliever and conflicts with their next assignment.",
                tool_calls=[],
                stop_reason="end_turn",
            ),
        ]
    )
    client = make_client(db, provider)

    response = client.post("/api/assistant/chat", json={"message": "What happens if Chain A stays another 14 days?"})

    assert response.status_code == 200
    sim_result = response.json()["tool_results"][0]["result"]
    categories = {e["category"] for e in sim_result["events"]}
    assert "reliever_affected" in categories
    assert "reliever_next_assignment_conflict" in categories
    assert "downstream_coverage_loss" in categories
    assert sim_result["is_destructive"] is False


def test_chat_endpoint_returns_503_when_llm_not_configured(db):
    """Exercises the real require_llm_provider wrapper (not an
    override of it) against the real get_llm_provider, which raises
    LLMNotConfiguredError whenever no LLM_API_KEY is set - the default
    in every local/CI environment."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides.pop(require_llm_provider, None)
    assert settings.llm_api_key is None, "this test assumes no LLM_API_KEY is configured"
    client = TestClient(app)

    response = client.post("/api/assistant/chat", json={"message": "Hello"})

    assert response.status_code == 503


def test_chat_endpoint_rejects_empty_message(db):
    provider = FakeProvider(script=[])
    client = make_client(db, provider)

    response = client.post("/api/assistant/chat", json={"message": ""})

    assert response.status_code == 422
