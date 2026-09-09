"""
The AI-accessible tool layer.

Every function in this module wraps an existing domain function from
app/domain/ - none of them re-decide eligibility, staffing, relief
timing, or simulation impact. Each tool:

  1. resolves any plain-language names (employee, site) to database
     rows, asking for clarification (never guessing) if a name is
     ambiguous or not found,
  2. calls exactly one existing domain function,
  3. converts the result to a small, JSON-serializable dict using the
     project's existing Pydantic schemas (app/schemas/), the same ones
     the REST API already returns to the frontend.

The LLM never sees raw ORM objects or SQL - only these dicts. If a
rule ever needs to change, it changes in app/domain/ and every caller
(this tool layer included) picks it up automatically, because none of
that logic is duplicated here.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.ai.employee_lookup import AmbiguousEmployeeError, EmployeeNotFoundError, resolve_employee_by_name
from app.domain.eligibility import evaluate_replacement_eligibility
from app.domain.employee_view import current_assignment
from app.domain.relief import get_relief_due as domain_get_relief_due
from app.domain.replacement import AssignmentNotFoundError
from app.domain.replacement import find_replacement_candidates as domain_find_replacement_candidates
from app.domain.simulation import simulate_extension as domain_simulate_extension
from app.domain.staffing import get_staffing_coverage
from app.models import Employee, Role, Site
from app.models.enums import EmploymentStatus
from app.schemas.common import EligibilityResultSchema
from app.schemas.relief import ReliefDueItemSchema
from app.schemas.replacement import ReplacementSearchResponseSchema
from app.schemas.simulation import ExtensionSimulationResponseSchema
from app.schemas.site import StaffingCoverageSchema

# Caps on how many candidates/rows a tool result includes, so the LLM
# is never handed an unbounded database dump - see the module and
# product docs on keeping tool output "small and structured".
MAX_LIST_ITEMS = 15
MAX_REJECTED_SHOWN = 5


def _ambiguous_response(err: AmbiguousEmployeeError) -> dict:
    return {
        "status": "ambiguous",
        "message": (
            f"More than one employee matches '{err.name}'. Ask the user which one they mean, "
            "using the distinguishing details below - never guess."
        ),
        "candidates": [
            {"id": m.id, "full_name": m.full_name, "role": m.role_name, "site": m.site_name} for m in err.matches
        ],
    }


def _not_found_response(err: EmployeeNotFoundError) -> dict:
    return {"status": "not_found", "message": f"No employee named '{err.name}' was found in Kinvera's records."}


def _resolve_or_none(db: Session, name: str) -> tuple[Employee | None, dict | None]:
    """Returns (employee, None) on success, or (None, error_dict) to
    hand straight back to the LLM as the tool's result."""
    try:
        return resolve_employee_by_name(db, name), None
    except AmbiguousEmployeeError as err:
        return None, _ambiguous_response(err)
    except EmployeeNotFoundError as err:
        return None, _not_found_response(err)


def _resolve_site_id(db: Session, site_name: str) -> tuple[int | None, dict | None]:
    matches = db.query(Site).filter(Site.name.ilike(f"%{site_name}%")).all()
    if not matches:
        return None, {"status": "not_found", "message": f"No site named '{site_name}' was found."}
    if len(matches) > 1:
        exact = [s for s in matches if s.name.lower() == site_name.strip().lower()]
        if len(exact) == 1:
            return exact[0].id, None
        return None, {
            "status": "ambiguous",
            "message": f"More than one site matches '{site_name}'. Ask the user which one they mean.",
            "candidates": [{"id": s.id, "name": s.name, "location": s.location} for s in matches],
        }
    return matches[0].id, None


# ---------------------------------------------------------------
# Tool 1: search_employees
# ---------------------------------------------------------------


def search_employees(
    db: Session, *, name: str | None = None, role: str | None = None, site: str | None = None, status: str | None = None
) -> dict:
    query = db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE)

    if name:
        pattern = f"%{name}%"
        full_name = func.concat(Employee.first_name, " ", Employee.last_name)
        query = query.filter(
            or_(Employee.first_name.ilike(pattern), Employee.last_name.ilike(pattern), full_name.ilike(pattern))
        )
    if role:
        query = query.join(Role).filter(Role.name.ilike(f"%{role}%"))
    if status:
        query = query.filter(Employee.availability_status == status.lower().replace(" ", "_"))

    employees = query.order_by(Employee.last_name, Employee.first_name).all()

    if site:
        site_lower = site.lower()
        employees = [
            e
            for e in employees
            if (a := current_assignment(e)) is not None and site_lower in a.site.name.lower()
        ]

    total = len(employees)
    rows = []
    for employee in employees[:MAX_LIST_ITEMS]:
        assignment = current_assignment(employee)
        rows.append(
            {
                "id": employee.id,
                "full_name": employee.full_name,
                "role": employee.role.name,
                "site": assignment.site.name if assignment else None,
                "availability_status": employee.availability_status.value,
            }
        )
    return {"status": "ok", "total_matches": total, "shown": len(rows), "employees": rows}


# ---------------------------------------------------------------
# Tool 2: get_relief_due
# ---------------------------------------------------------------


def get_relief_due_tool(db: Session, *, days: int = 30) -> dict:
    items = domain_get_relief_due(db, window_days=days)
    schemas = [ReliefDueItemSchema.from_domain(i).model_dump(mode="json") for i in items[:MAX_LIST_ITEMS]]
    for row in schemas:
        row.pop("assignment_id", None)
        row.pop("role_id", None)
        row.pop("site_id", None)
        row.pop("reliever_employee_id", None)
        row.pop("reliever_assignment_id", None)
    return {"status": "ok", "window_days": days, "total_matches": len(items), "shown": len(schemas), "items": schemas}


# ---------------------------------------------------------------
# Tool 3: evaluate_replacement
# ---------------------------------------------------------------


def evaluate_replacement(db: Session, *, candidate_name: str, target_employee_name: str) -> dict:
    target, error = _resolve_or_none(db, target_employee_name)
    if error:
        return error
    target_assignment = current_assignment(target)
    if target_assignment is None:
        return {"status": "error", "message": f"{target.full_name} has no current assignment to replace."}

    candidate, error = _resolve_or_none(db, candidate_name)
    if error:
        return error

    window_start = max(target_assignment.start_date, date.today())
    window_end = target_assignment.planned_end_date

    result = evaluate_replacement_eligibility(
        db,
        candidate,
        role_id=target_assignment.role_id,
        site_id=target_assignment.site_id,
        window_start=window_start,
        window_end=window_end,
    )
    payload = EligibilityResultSchema.from_domain(result).model_dump(mode="json")
    return {
        "status": "ok",
        "target_employee_name": target.full_name,
        "target_site": target_assignment.site.name,
        **payload,
    }


# ---------------------------------------------------------------
# Tool 4: find_replacement_candidates
# ---------------------------------------------------------------


def find_replacement_candidates_tool(db: Session, *, employee_name: str) -> dict:
    target, error = _resolve_or_none(db, employee_name)
    if error:
        return error
    target_assignment = current_assignment(target)
    if target_assignment is None:
        return {
            "status": "error",
            "message": f"{target.full_name} has no current assignment to find a replacement for.",
        }

    try:
        result = domain_find_replacement_candidates(db, target_assignment.id)
    except AssignmentNotFoundError as exc:
        return {"status": "error", "message": str(exc)}

    schema = ReplacementSearchResponseSchema.from_domain(result)
    eligible = [{"employee_name": c.employee_name, "summary": c.summary} for c in schema.eligible_candidates]
    rejected_all = schema.rejected_candidates
    rejected = [
        {
            "employee_name": c.employee_name,
            "reason": next((chk.reason for chk in c.checks if not chk.passed), "Not eligible."),
        }
        for c in rejected_all[:MAX_REJECTED_SHOWN]
    ]

    return {
        "status": "ok",
        "target_employee_name": schema.target_employee_name,
        "role_name": schema.role_name,
        "site_name": schema.site_name,
        "window_start": str(schema.window_start),
        "window_end": str(schema.window_end),
        "eligible_count": len(eligible),
        "eligible_candidates": eligible,
        "rejected_count": len(rejected_all),
        "rejected_candidates_shown": rejected,
    }


# ---------------------------------------------------------------
# Tool 5: simulate_extension
# ---------------------------------------------------------------


def simulate_extension_tool(db: Session, *, employee_name: str, extension_days: int) -> dict:
    target, error = _resolve_or_none(db, employee_name)
    if error:
        return error
    target_assignment = current_assignment(target)
    if target_assignment is None:
        return {"status": "error", "message": f"{target.full_name} has no current assignment to extend."}

    try:
        result = domain_simulate_extension(db, target_assignment.id, extension_days)
    except AssignmentNotFoundError as exc:
        return {"status": "error", "message": str(exc)}

    schema = ExtensionSimulationResponseSchema.from_domain(result)
    return {
        "status": "ok",
        "is_destructive": schema.is_destructive,
        "employee_name": schema.employee_name,
        "extension_days": schema.extension_days,
        "original_planned_end_date": str(schema.original_planned_end_date),
        "simulated_planned_end_date": str(schema.simulated_planned_end_date),
        "overall_severity": schema.overall_severity,
        "events": [e.model_dump(mode="json") for e in schema.events],
        "staffing_impacts": [s.model_dump(mode="json") for s in schema.staffing_impacts],
        "eligible_alternatives": [
            {"employee_name": c.employee_name, "summary": c.summary} for c in schema.eligible_alternatives
        ],
        "rejected_alternatives_shown": [
            {
                "employee_name": c.employee_name,
                "reason": next((chk.reason for chk in c.checks if not chk.passed), "Not eligible."),
            }
            for c in schema.rejected_alternatives[:MAX_REJECTED_SHOWN]
        ],
        "rejected_alternatives_count": len(schema.rejected_alternatives),
    }


# ---------------------------------------------------------------
# Tool 6: get_staffing_status
# ---------------------------------------------------------------


def get_staffing_status(db: Session, *, site_name: str | None = None, shortages_only: bool = False) -> dict:
    site_id = None
    if site_name:
        site_id, error = _resolve_site_id(db, site_name)
        if error:
            return error

    coverage = get_staffing_coverage(db, site_id=site_id)
    if shortages_only:
        coverage = [c for c in coverage if c.shortage > 0]

    rows = [StaffingCoverageSchema.from_domain(c).model_dump(mode="json") for c in coverage]
    return {"status": "ok", "count": len(rows), "coverage": rows}


# ---------------------------------------------------------------
# Tool registry: what the LLM is told exists, and how to call it
# ---------------------------------------------------------------


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for the tool's input
    handler: Callable[..., dict]


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="search_employees",
        description=(
            "Search Kinvera's employee records by name, role, site, or availability status. "
            "Use this to find an employee or list who matches a description."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full or partial employee name."},
                "role": {"type": "string", "description": "Role name, e.g. 'Senior Field Technician'."},
                "site": {"type": "string", "description": "Site name, e.g. 'Northfield Compression Station'."},
                "status": {
                    "type": "string",
                    "description": "Availability status: available, assigned, on_leave, or unavailable.",
                },
            },
        },
        handler=search_employees,
    ),
    ToolSpec(
        name="get_relief_due",
        description=(
            "Return active assignments whose planned end falls within the given number of days "
            "- i.e. who needs relief soon."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Lookahead window in days.", "default": 30},
            },
        },
        handler=get_relief_due_tool,
    ),
    ToolSpec(
        name="evaluate_replacement",
        description=(
            "Deterministically evaluate whether one specific employee (candidate_name) is eligible to replace "
            "another specific employee's (target_employee_name) current assignment. Use this whenever the user "
            "asks 'can X replace Y' about two named employees."
        ),
        parameters={
            "type": "object",
            "properties": {
                "candidate_name": {"type": "string", "description": "The employee being considered as a replacement."},
                "target_employee_name": {"type": "string", "description": "The employee who would be replaced."},
            },
            "required": ["candidate_name", "target_employee_name"],
        },
        handler=evaluate_replacement,
    ),
    ToolSpec(
        name="find_replacement_candidates",
        description=(
            "Find every employee deterministically eligible (and a sample of those rejected, with reasons) to "
            "replace a named employee's current assignment. Use this for 'who can replace X' questions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "employee_name": {"type": "string", "description": "The employee to find a replacement for."},
            },
            "required": ["employee_name"],
        },
        handler=find_replacement_candidates_tool,
    ),
    ToolSpec(
        name="simulate_extension",
        description=(
            "Run Kinvera's non-destructive extension-impact simulation: what would happen if a named employee's "
            "current assignment ran N more days. Never modifies any record - this is a preview only."
        ),
        parameters={
            "type": "object",
            "properties": {
                "employee_name": {"type": "string", "description": "The employee whose assignment would be extended."},
                "extension_days": {"type": "integer", "description": "Number of days to extend by."},
            },
            "required": ["employee_name", "extension_days"],
        },
        handler=simulate_extension_tool,
    ),
    ToolSpec(
        name="get_staffing_status",
        description=(
            "Return current staffing coverage (assigned vs. minimum required) by site and role, "
            "optionally filtered to one site or to shortages only."
        ),
        parameters={
            "type": "object",
            "properties": {
                "site_name": {"type": "string", "description": "Optional site name to filter to."},
                "shortages_only": {
                    "type": "boolean",
                    "description": "If true, only return site/role pairs below minimum.",
                    "default": False,
                },
            },
        },
        handler=get_staffing_status,
    ),
]

TOOLS_BY_NAME: dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}


def execute_tool(db: Session, name: str, arguments: dict[str, Any]) -> dict:
    """Look up and run a tool by name. This is the only place a tool
    name from the LLM turns into an actual function call - there is no
    other path from "the model said to call X" to code execution."""
    spec = TOOLS_BY_NAME.get(name)
    if spec is None:
        return {"status": "error", "message": f"Unknown tool '{name}'."}
    try:
        return spec.handler(db, **arguments)
    except TypeError as exc:
        return {"status": "error", "message": f"Invalid arguments for '{name}': {exc}"}
