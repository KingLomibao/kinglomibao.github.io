"""
Deriving a qualification's validity status from its dates.

A qualification's status is never stored as its own column - storing
"expired" as a boolean next to an `expiry_date` risks the two silently
disagreeing the day after the date passes. Instead, status is always
computed from `expiry_date` compared to the current date, in exactly
one place.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Employee, EmployeeQualification
from app.models.enums import EmploymentStatus

EXPIRING_SOON_THRESHOLD_DAYS = 30


def qualification_status(expiry_date: date, *, reference_date: date | None = None) -> str:
    """Returns "expired", "expiring_soon", or "valid"."""
    today = reference_date or date.today()
    if expiry_date < today:
        return "expired"
    if expiry_date <= today + timedelta(days=EXPIRING_SOON_THRESHOLD_DAYS):
        return "expiring_soon"
    return "valid"


def list_qualification_risks(
    db: Session, *, reference_date: date | None = None
) -> list[EmployeeQualification]:
    """Every qualification held by an active employee that is expired
    or expiring soon, most urgent first."""
    today = reference_date or date.today()
    at_risk = (
        db.query(EmployeeQualification)
        .join(Employee)
        .filter(Employee.employment_status == EmploymentStatus.ACTIVE)
        .filter(EmployeeQualification.expiry_date <= today + timedelta(days=EXPIRING_SOON_THRESHOLD_DAYS))
        .order_by(EmployeeQualification.expiry_date)
        .all()
    )
    return at_risk
