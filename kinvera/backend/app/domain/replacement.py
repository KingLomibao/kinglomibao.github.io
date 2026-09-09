"""
Replacement search: "who can replace this person?"

This module does the lookup work (find the assignment, work out the
role/window/site it requires, gather candidates) and then hands every
candidate to the shared eligibility engine in eligibility.py. It never
evaluates eligibility itself - that would risk this search disagreeing
with the extension-simulation engine about who is eligible.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.domain.eligibility import evaluate_replacement_eligibility
from app.domain.results import EligibilityResult
from app.models import Assignment, Employee
from app.models.enums import EmploymentStatus


class AssignmentNotFoundError(ValueError):
    pass


@dataclass
class ReplacementSearchResult:
    target_assignment_id: int
    target_employee_id: int
    target_employee_name: str
    role_id: int
    role_name: str
    site_id: int
    site_name: str
    window_start: date
    window_end: date
    eligible_candidates: list[EligibilityResult] = field(default_factory=list)
    rejected_candidates: list[EligibilityResult] = field(default_factory=list)


def find_replacement_candidates(
    db: Session,
    assignment_id: int,
    *,
    reference_date: date | None = None,
) -> ReplacementSearchResult:
    """Find employees eligible to replace whoever holds `assignment_id`.

    The required window runs from `reference_date` (or the
    assignment's start date, if it hasn't started yet) through the
    assignment's planned end date - i.e. "if this person had to be
    replaced right now, who could step in for the remainder of this
    assignment?".
    """
    target = db.get(Assignment, assignment_id)
    if target is None:
        raise AssignmentNotFoundError(f"Assignment {assignment_id} not found.")

    today = reference_date or date.today()
    window_start = max(target.start_date, today)
    window_end = target.planned_end_date

    candidates = (
        db.query(Employee)
        .filter(
            Employee.role_id == target.role_id,
            Employee.id != target.employee_id,
            Employee.employment_status == EmploymentStatus.ACTIVE,
        )
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )

    result = ReplacementSearchResult(
        target_assignment_id=target.id,
        target_employee_id=target.employee_id,
        target_employee_name=target.employee.full_name,
        role_id=target.role_id,
        role_name=target.role.name,
        site_id=target.site_id,
        site_name=target.site.name,
        window_start=window_start,
        window_end=window_end,
    )

    for candidate in candidates:
        evaluation = evaluate_replacement_eligibility(
            db,
            candidate,
            role_id=target.role_id,
            site_id=target.site_id,
            window_start=window_start,
            window_end=window_end,
        )
        if evaluation.eligible:
            result.eligible_candidates.append(evaluation)
        else:
            result.rejected_candidates.append(evaluation)

    return result
