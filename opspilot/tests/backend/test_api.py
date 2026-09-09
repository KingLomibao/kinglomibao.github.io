"""
Integration tests for the FastAPI layer.

These exercise the actual HTTP routes (via FastAPI's TestClient)
against a database seeded through the same factories used elsewhere,
confirming the API wiring - dependency overrides, request/response
schemas, status codes - works end-to-end, not just the domain layer
underneath it.
"""

from datetime import timedelta

from factories import TODAY, make_assignment, make_employee, make_role, make_site, make_staffing_requirement
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def make_client(db) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    return client


def test_health_check(db):
    client = make_client(db)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_summary_endpoint(db):
    role, site = make_role(db), make_site(db)
    make_staffing_requirement(db, site, role, 1)
    client = make_client(db)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert "total_active_workforce" in body
    assert "staffing_shortages" in body


def test_employee_detail_not_found_returns_404(db):
    client = make_client(db)
    response = client.get("/api/employees/999999")
    assert response.status_code == 404


def test_replacement_candidates_endpoint(db):
    role, site = make_role(db), make_site(db)
    target = make_employee(db, role)
    make_employee(db, role)  # a candidate
    assignment = make_assignment(
        db, target, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )
    client = make_client(db)

    response = client.get(f"/api/assignments/{assignment.id}/replacement-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["target_employee_id"] == target.id
    assert len(body["eligible_candidates"]) == 1


def test_simulate_extension_endpoint_is_non_destructive(db):
    role, site = make_role(db), make_site(db)
    employee = make_employee(db, role)
    assignment = make_assignment(
        db, employee, site, role, start_date=TODAY - timedelta(days=5), planned_end_date=TODAY + timedelta(days=20)
    )
    client = make_client(db)

    response = client.post(f"/api/assignments/{assignment.id}/simulate-extension", json={"extension_days": 14})

    assert response.status_code == 200
    body = response.json()
    assert body["is_destructive"] is False
    assert body["simulated_planned_end_date"] == str(TODAY + timedelta(days=34))

    # Confirm the API call really did not persist a change.
    fresh = client.get(f"/api/assignments/{assignment.id}")
    assert fresh.json()["planned_end_date"] == str(TODAY + timedelta(days=20))
