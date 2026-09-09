"""
FastAPI application entry point.

This file wires the app together (CORS, routers) and nothing else -
every route handler lives in app/api/routes/ and every route handler
delegates the actual decision-making to app/domain/. Run it with:

    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assignments,
    dashboard,
    employees,
    movements,
    qualifications,
    relief,
    replacement,
    simulation,
    sites,
    staffing,
)
from app.core.config import settings

app = FastAPI(
    title="Kinvera API",
    description=(
        "Deterministic workforce operations API for Ironbridge Field Operations. "
        "AI explains; business rules decide - every eligibility, relief, staffing, "
        "and simulation result here comes from ordinary, testable Python evaluating "
        "database records, never from a language model."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(employees.router)
app.include_router(sites.router)
app.include_router(staffing.router)
app.include_router(assignments.router)
app.include_router(movements.router)
app.include_router(qualifications.router)
app.include_router(relief.router)
app.include_router(replacement.router)
app.include_router(simulation.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
