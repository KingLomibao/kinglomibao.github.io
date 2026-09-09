"""
Staffing coverage: minimum required vs. actually assigned headcount,
by site and role.

Phase 1 deliberately keeps this to a single number per site+role
(SiteStaffingRequirement) rather than a scheduling/optimization model.
That is enough to answer two questions deterministically:
  - Right now, is any site short-staffed for a role? (get_staffing_coverage)
  - If we're looking at some future date window (e.g. while simulating
    an extension), would headcount for a role at a site drop below the
    minimum during that window? (count_role_coverage)
"""

from datetime import date

from sqlalchemy.orm import Session

from app.domain.dates import overlaps_inclusive
from app.domain.results import StaffingCoverageItem
from app.models import Assignment, SiteStaffingRequirement
from app.models.enums import AssignmentStatus


def get_staffing_coverage(db: Session, *, site_id: int | None = None) -> list[StaffingCoverageItem]:
    """Current (as-of-today) staffing coverage for every site+role that
    has a defined minimum requirement."""
    query = db.query(SiteStaffingRequirement)
    if site_id is not None:
        query = query.filter(SiteStaffingRequirement.site_id == site_id)
    requirements = query.all()

    items = []
    for requirement in requirements:
        currently_assigned = (
            db.query(Assignment)
            .filter(
                Assignment.site_id == requirement.site_id,
                Assignment.role_id == requirement.role_id,
                Assignment.status == AssignmentStatus.ACTIVE,
            )
            .count()
        )
        items.append(
            StaffingCoverageItem(
                site_id=requirement.site_id,
                site_name=requirement.site.name,
                role_id=requirement.role_id,
                role_name=requirement.role.name,
                minimum_required=requirement.minimum_required,
                currently_assigned=currently_assigned,
            )
        )
    return items


def get_staffing_shortages(db: Session, *, site_id: int | None = None) -> list[StaffingCoverageItem]:
    return [item for item in get_staffing_coverage(db, site_id=site_id) if item.shortage > 0]


def count_role_coverage(
    db: Session,
    *,
    site_id: int,
    role_id: int,
    window_start: date,
    window_end: date,
    exclude_assignment_ids: tuple[int, ...] = (),
) -> int:
    """How many people would realistically be covering this role at
    this site at some point during [window_start, window_end]?

    Used by the extension-simulation engine to check whether a
    proposed change leaves a gap - boundaries are inclusive here
    (unlike the eligibility engine's overlap check) because this is
    asking "is anyone present on these days", not "is this a
    double-booking".
    """
    candidates = (
        db.query(Assignment)
        .filter(
            Assignment.site_id == site_id,
            Assignment.role_id == role_id,
            Assignment.status.in_([AssignmentStatus.ACTIVE, AssignmentStatus.PLANNED]),
        )
        .all()
    )
    count = 0
    for assignment in candidates:
        if assignment.id in exclude_assignment_ids:
            continue
        effective_end = assignment.actual_end_date or assignment.planned_end_date
        if overlaps_inclusive(window_start, window_end, assignment.start_date, effective_end):
            count += 1
    return count
