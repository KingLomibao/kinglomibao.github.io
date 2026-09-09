"""
Assignment-extension impact simulation: "what happens if this person
stays N more days?"

This is a read-only, non-destructive calculation. It never writes the
proposed new end date to the database - it works entirely with local
Python values and only *reads* other records to figure out what a
change would collide with.

The simulation walks one hop of the relief chain:

    target assignment (being extended)
        -> its planned reliever, if any
            -> the reliever's own next assignment, if any
                -> whoever THAT next assignment was going to relieve

At each hop it asks a concrete question ("does the reliever's start
date still work?", "does their next commitment now overlap?", "does
that leave the next site short-staffed?") and, when a gap appears,
reuses the same eligibility engine every other part of the app uses to
look for someone who could cover it. Phase 1 deliberately walks only
this one hop rather than an arbitrary-depth chain - deep enough to
demonstrate a real, multi-site downstream conflict without turning
into an open-ended scheduling solver.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.domain.dates import overlaps_exclusive
from app.domain.eligibility import evaluate_replacement_eligibility
from app.domain.results import ExtensionSimulationResult, ImpactEvent, StaffingCoverageItem
from app.models import Assignment, Employee, SiteStaffingRequirement
from app.models.enums import AssignmentStatus, EmploymentStatus


class AssignmentNotFoundError(ValueError):
    pass


def _find_direct_reliever(db: Session, assignment_id: int) -> Assignment | None:
    return (
        db.query(Assignment)
        .filter(
            Assignment.relieving_assignment_id == assignment_id,
            Assignment.status != AssignmentStatus.CANCELLED,
        )
        .order_by(Assignment.start_date)
        .first()
    )


def _find_next_conflicting_assignment(
    employee: Employee, *, after_assignment_id: int, window_start: date, window_end: date
) -> Assignment | None:
    """Among `employee`'s other commitments, find one whose window
    overlaps [window_start, window_end] - i.e. a commitment this
    person can no longer keep if they are stuck here that long."""
    for assignment in employee.assignments:
        if assignment.id == after_assignment_id or assignment.status == AssignmentStatus.CANCELLED:
            continue
        effective_end = assignment.actual_end_date or assignment.planned_end_date
        if overlaps_exclusive(window_start, window_end, assignment.start_date, effective_end):
            return assignment
    return None


def simulate_extension(
    db: Session,
    assignment_id: int,
    extension_days: int,
    *,
    reference_date: date | None = None,
) -> ExtensionSimulationResult:
    target = db.get(Assignment, assignment_id)
    if target is None:
        raise AssignmentNotFoundError(f"Assignment {assignment_id} not found.")

    original_end = target.planned_end_date
    simulated_end = original_end + timedelta(days=extension_days)

    result = ExtensionSimulationResult(
        assignment_id=target.id,
        employee_id=target.employee_id,
        employee_name=target.employee.full_name,
        extension_days=extension_days,
        original_planned_end_date=original_end,
        simulated_planned_end_date=simulated_end,
    )

    reliever = _find_direct_reliever(db, target.id)
    if reliever is None:
        result.events.append(
            ImpactEvent(
                category="extension",
                description=(
                    f"{target.employee.full_name}'s assignment at {target.site.name} would run "
                    f"through {simulated_end.isoformat()} instead of {original_end.isoformat()}. "
                    "No reliever is currently planned for this assignment, so no downstream "
                    "conflict was detected."
                ),
                severity="info",
                employee_id=target.employee_id,
                assignment_id=target.id,
                site_id=target.site_id,
            )
        )
        return result

    result.events.append(
        ImpactEvent(
            category="extension",
            description=(
                f"{target.employee.full_name}'s assignment at {target.site.name} would run through "
                f"{simulated_end.isoformat()} instead of {original_end.isoformat()}."
            ),
            severity="info",
            employee_id=target.employee_id,
            assignment_id=target.id,
            site_id=target.site_id,
        )
    )

    reliever_delayed = simulated_end > reliever.start_date
    if not reliever_delayed:
        result.events.append(
            ImpactEvent(
                category="reliever_unaffected",
                description=(
                    f"{reliever.employee.full_name}'s planned start date of "
                    f"{reliever.start_date.isoformat()} already falls on or after the new end date, "
                    "so their schedule is unaffected."
                ),
                severity="info",
                employee_id=reliever.employee_id,
                assignment_id=reliever.id,
                site_id=reliever.site_id,
            )
        )
        return result

    delay_days = (simulated_end - reliever.start_date).days
    reliever_duration = reliever.planned_end_date - reliever.start_date
    shifted_start = simulated_end
    shifted_end = shifted_start + reliever_duration

    result.events.append(
        ImpactEvent(
            category="reliever_affected",
            description=(
                f"{reliever.employee.full_name} was due to relieve {target.employee.full_name} on "
                f"{reliever.start_date.isoformat()}, but that would now be delayed by {delay_days} day(s) "
                f"to {shifted_start.isoformat()}."
            ),
            severity="medium",
            employee_id=reliever.employee_id,
            assignment_id=reliever.id,
            site_id=reliever.site_id,
        )
    )

    next_assignment = _find_next_conflicting_assignment(
        reliever.employee, after_assignment_id=reliever.id, window_start=shifted_start, window_end=shifted_end
    )
    if next_assignment is None:
        result.events.append(
            ImpactEvent(
                category="no_further_conflict",
                description=(
                    f"{reliever.employee.full_name} has no other commitment during the delayed window, "
                    "so no further downstream conflict was detected."
                ),
                severity="low",
                employee_id=reliever.employee_id,
            )
        )
        return result

    result.events.append(
        ImpactEvent(
            category="reliever_next_assignment_conflict",
            description=(
                f"{reliever.employee.full_name} is already committed to relieve at "
                f"{next_assignment.site.name} starting {next_assignment.start_date.isoformat()}, "
                f"which now overlaps with the delayed relief at {target.site.name}."
            ),
            severity="high",
            employee_id=reliever.employee_id,
            assignment_id=next_assignment.id,
            site_id=next_assignment.site_id,
        )
    )

    # Who was `next_assignment` itself going to relieve? That person's
    # site now loses its expected coverage for the delay period.
    gap_start = next_assignment.start_date
    gap_end = shifted_end
    downstream_relieved = (
        db.get(Assignment, next_assignment.relieving_assignment_id)
        if next_assignment.relieving_assignment_id
        else None
    )
    if downstream_relieved is not None:
        result.events.append(
            ImpactEvent(
                category="downstream_coverage_loss",
                description=(
                    f"{next_assignment.site.name} expected {reliever.employee.full_name} to relieve "
                    f"{downstream_relieved.employee.full_name} on {gap_start.isoformat()}, but coverage "
                    f"would now be missing there until {gap_end.isoformat()}."
                ),
                severity="high",
                employee_id=downstream_relieved.employee_id,
                assignment_id=downstream_relieved.id,
                site_id=next_assignment.site_id,
            )
        )

    exclude_ids = {next_assignment.id}
    if downstream_relieved is not None:
        exclude_ids.add(downstream_relieved.id)

    from app.domain.staffing import count_role_coverage  # local import avoids a cycle at module load time

    coverage_during_gap = count_role_coverage(
        db,
        site_id=next_assignment.site_id,
        role_id=next_assignment.role_id,
        window_start=gap_start,
        window_end=gap_end,
        exclude_assignment_ids=tuple(exclude_ids),
    )

    requirement = (
        db.query(SiteStaffingRequirement)
        .filter(
            SiteStaffingRequirement.site_id == next_assignment.site_id,
            SiteStaffingRequirement.role_id == next_assignment.role_id,
        )
        .first()
    )
    shortage_detected = False
    if requirement is not None:
        coverage_item = StaffingCoverageItem(
            site_id=next_assignment.site_id,
            site_name=next_assignment.site.name,
            role_id=next_assignment.role_id,
            role_name=next_assignment.role.name,
            minimum_required=requirement.minimum_required,
            currently_assigned=coverage_during_gap,
        )
        result.staffing_impacts.append(coverage_item)
        if coverage_item.shortage > 0:
            shortage_detected = True
            result.events.append(
                ImpactEvent(
                    category="staffing_shortage",
                    description=(
                        f"{next_assignment.site.name} requires {requirement.minimum_required} "
                        f"{next_assignment.role.name}(s) but would only have {coverage_during_gap} "
                        f"from {gap_start.isoformat()} to {gap_end.isoformat()}."
                    ),
                    severity="high",
                    site_id=next_assignment.site_id,
                )
            )

    # Reuse the standard eligibility engine to look for someone who
    # could cover the gap at next_assignment's site/role/window -
    # never a separate, simulation-only notion of "eligible".
    # The reliever is already accounted for above (they're the one
    # delayed), and the target employee cannot cover this gap either -
    # they are, by hypothesis, the very person still tied up at their
    # own site for the extended period.
    ineligible_by_construction = {reliever.employee_id, target.employee_id}
    candidates = (
        db.query(Employee)
        .filter(
            Employee.role_id == next_assignment.role_id,
            Employee.employment_status == EmploymentStatus.ACTIVE,
            Employee.id.notin_(ineligible_by_construction),
        )
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )
    for candidate in candidates:
        evaluation = evaluate_replacement_eligibility(
            db,
            candidate,
            role_id=next_assignment.role_id,
            site_id=next_assignment.site_id,
            window_start=gap_start,
            window_end=gap_end,
            exclude_assignment_id=next_assignment.id,
        )
        if evaluation.eligible:
            result.eligible_alternatives.append(evaluation)
        else:
            result.rejected_alternatives.append(evaluation)

    if not shortage_detected and requirement is None:
        result.events.append(
            ImpactEvent(
                category="coverage_reduced",
                description=(
                    f"{next_assignment.site.name} has no defined minimum staffing level for "
                    f"{next_assignment.role.name}, but coverage would be reduced from "
                    f"{gap_start.isoformat()} to {gap_end.isoformat()}."
                ),
                severity="low",
                site_id=next_assignment.site_id,
            )
        )

    return result
