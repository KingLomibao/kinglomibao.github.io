"""
Relief-due logic: "who needs relief in the next N days?"

The lookahead window is a parameter, not a hard-coded 30, so the
dashboard, the API, and the tests can all ask for different windows
without touching this function.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.results import ReliefDueItem
from app.models import Assignment
from app.models.enums import AssignmentStatus


def get_relief_due(
    db: Session,
    *,
    window_days: int | None = None,
    reference_date: date | None = None,
) -> list[ReliefDueItem]:
    """Active assignments whose planned end falls within the window.

    An assignment already marked COMPLETED never appears here, even if
    its planned end date is technically inside the window - relief for
    it already happened (or was resolved some other way). An ACTIVE
    assignment whose planned end date has already passed is still
    included and flagged "overdue", since that person is still
    deployed past when they were meant to be relieved.
    """
    if window_days is None:
        window_days = settings.default_relief_window_days
    today = reference_date or date.today()
    window_end_date = today + timedelta(days=window_days)

    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.status == AssignmentStatus.ACTIVE,
            Assignment.planned_end_date <= window_end_date,
        )
        .order_by(Assignment.planned_end_date)
        .all()
    )

    items: list[ReliefDueItem] = []
    for assignment in assignments:
        # Find the (at most one, by construction) assignment that
        # names this one as the assignment it relieves.
        reliever = (
            db.query(Assignment)
            .filter(
                Assignment.relieving_assignment_id == assignment.id,
                Assignment.status != AssignmentStatus.CANCELLED,
            )
            .order_by(Assignment.start_date)
            .first()
        )

        days_remaining = (assignment.planned_end_date - today).days
        if days_remaining < 0:
            risk = "overdue"
        elif reliever is None:
            risk = "no_reliever"
        else:
            risk = "reliever_planned"

        items.append(
            ReliefDueItem(
                assignment_id=assignment.id,
                employee_id=assignment.employee_id,
                employee_name=assignment.employee.full_name,
                role_id=assignment.role_id,
                role_name=assignment.role.name,
                site_id=assignment.site_id,
                site_name=assignment.site.name,
                planned_end_date=assignment.planned_end_date,
                days_remaining=days_remaining,
                reliever_employee_id=reliever.employee_id if reliever else None,
                reliever_employee_name=reliever.employee.full_name if reliever else None,
                reliever_assignment_id=reliever.id if reliever else None,
                reliever_status="planned" if reliever else "none",
                risk=risk,
            )
        )

    return items
