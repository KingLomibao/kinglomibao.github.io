"""
Small helpers for assembling a single employee's operational picture
(current assignment, next planned assignment, recent movements).

These aren't "business rules" in the eligibility/staffing sense - they
don't decide anything - but they're still logic about what an
assignment record *means*, so they live here rather than being
duplicated inline wherever an employee's detail view is built.
"""

from app.models import Assignment, Employee
from app.models.enums import AssignmentStatus


def current_assignment(employee: Employee) -> Assignment | None:
    active = [a for a in employee.assignments if a.status == AssignmentStatus.ACTIVE]
    return min(active, key=lambda a: a.start_date) if active else None


def next_planned_assignment(employee: Employee) -> Assignment | None:
    planned = [a for a in employee.assignments if a.status == AssignmentStatus.PLANNED]
    return min(planned, key=lambda a: a.start_date) if planned else None


def assignment_history(employee: Employee, *, limit: int = 5) -> list[Assignment]:
    completed = [a for a in employee.assignments if a.status == AssignmentStatus.COMPLETED]
    completed.sort(key=lambda a: a.actual_end_date or a.planned_end_date, reverse=True)
    return completed[:limit]
