"""
Assembles the main dashboard's KPI summary.

Every number here is produced by calling the same domain functions
that power their dedicated views (relief.py, staffing.py) or by a
direct, simple count - there is no separate "dashboard-only" version
of any rule.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.qualifications import qualification_status
from app.domain.relief import get_relief_due
from app.domain.results import DashboardSummary
from app.domain.staffing import get_staffing_shortages
from app.models import Employee, EmployeeQualification, Site
from app.models.enums import AvailabilityStatus, EmploymentStatus


def get_dashboard_summary(
    db: Session, *, relief_window_days: int | None = None, reference_date: date | None = None
) -> DashboardSummary:
    window_days = relief_window_days or settings.default_relief_window_days
    today = reference_date or date.today()

    active_employees = db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE)

    def count_by_availability(status: AvailabilityStatus) -> int:
        return active_employees.filter(Employee.availability_status == status).count()

    active_employee_qualifications = (
        db.query(EmployeeQualification).join(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE)
    )
    qualification_risks = sum(
        1
        for eq in active_employee_qualifications
        if qualification_status(eq.expiry_date, reference_date=today) in ("expired", "expiring_soon")
    )

    return DashboardSummary(
        total_active_workforce=active_employees.count(),
        currently_assigned=count_by_availability(AvailabilityStatus.ASSIGNED),
        available=count_by_availability(AvailabilityStatus.AVAILABLE),
        on_leave=count_by_availability(AvailabilityStatus.ON_LEAVE),
        unavailable=count_by_availability(AvailabilityStatus.UNAVAILABLE),
        relief_due_in_window=len(get_relief_due(db, window_days=window_days, reference_date=today)),
        relief_window_days=window_days,
        qualification_risks=qualification_risks,
        staffing_shortages=len(get_staffing_shortages(db)),
        total_sites=db.query(Site).count(),
    )
