"""
The replacement-eligibility engine.

This is the single source of truth for "can this person do this job,
at this site, for this date window?" - used by the replacement-search
endpoint, the extension-simulation engine, and (later) the AI
assistant's tool layer. It is never re-implemented anywhere else: the
simulation engine calls the exact same `evaluate_replacement_eligibility`
function used for an ordinary replacement search, so a candidate can
never be "eligible" in one part of the app and "ineligible" in another.

Every check is a named, independent rule that produces a pass/fail and
(on failure) a human-readable reason. Nothing here decides anything
based on free text or a language model - it is ordinary, deterministic
Python evaluated against database records.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.dates import overlaps_exclusive
from app.domain.results import EligibilityResult, RuleCheck
from app.models import Assignment, Employee, RoleQualificationRequirement
from app.models.enums import AssignmentStatus, AvailabilityStatus, EmploymentStatus


def _effective_end_date(assignment: Assignment) -> date:
    return assignment.actual_end_date or assignment.planned_end_date


def evaluate_replacement_eligibility(
    db: Session,
    candidate: Employee,
    *,
    role_id: int,
    site_id: int,
    window_start: date,
    window_end: date,
    exclude_assignment_id: int | None = None,
    minimum_rest_days: int | None = None,
) -> EligibilityResult:
    """Evaluate one candidate against one required assignment window.

    `site_id` is accepted (and recorded on the result) even though no
    current check depends on it, because it is part of what the result
    is *for* - and a future rule (e.g. a site-specific induction) would
    naturally need it.
    """
    if minimum_rest_days is None:
        minimum_rest_days = settings.minimum_rest_days

    checks: list[RuleCheck] = []

    # 1. Employee is active.
    is_active = candidate.active and candidate.employment_status == EmploymentStatus.ACTIVE
    checks.append(
        RuleCheck(
            rule="active_employment",
            passed=is_active,
            reason=None if is_active else f"{candidate.full_name} is not an active employee.",
        )
    )

    # 2. Required role matches. Phase 1 only supports an exact role
    # match - a future role-substitution rule (e.g. a Site Supervisor
    # may cover a Senior Field Technician gap) would be added as data,
    # not as a special case in this function.
    role_matches = candidate.role_id == role_id
    checks.append(
        RuleCheck(
            rule="role_match",
            passed=role_matches,
            reason=None
            if role_matches
            else f"{candidate.full_name} holds {candidate.role.name}, not the required role.",
        )
    )

    # 3. Employee is available (not on leave or otherwise unavailable).
    # Phase 1 approximates "available for the window" using the
    # employee's current availability snapshot rather than a full
    # leave calendar - see docs/business-rules.md for this limitation.
    is_available = candidate.availability_status not in (
        AvailabilityStatus.ON_LEAVE,
        AvailabilityStatus.UNAVAILABLE,
    )
    checks.append(
        RuleCheck(
            rule="availability_status",
            passed=is_available,
            reason=None
            if is_available
            else f"{candidate.full_name} is currently marked {candidate.availability_status.value.replace('_', ' ')}.",
        )
    )

    # 4. Every qualification the role mandates must be on file and
    # valid through the end of the required window - one check per
    # qualification, so a rejection always names the specific gap.
    requirements = (
        db.query(RoleQualificationRequirement)
        .filter(RoleQualificationRequirement.role_id == role_id, RoleQualificationRequirement.mandatory.is_(True))
        .all()
    )
    held_qualifications = {eq.qualification_id: eq for eq in candidate.qualifications}
    for requirement in requirements:
        qualification = requirement.qualification
        held = held_qualifications.get(requirement.qualification_id)
        if held is None:
            checks.append(
                RuleCheck(
                    rule=f"qualification_valid:{qualification.code}",
                    passed=False,
                    reason=f"{qualification.name} is not on file for {candidate.full_name}.",
                )
            )
        elif held.expiry_date < window_end:
            checks.append(
                RuleCheck(
                    rule=f"qualification_valid:{qualification.code}",
                    passed=False,
                    reason=(
                        f"{qualification.name} expires {held.expiry_date.isoformat()}, "
                        f"before the assignment ends {window_end.isoformat()}."
                    ),
                )
            )
        else:
            checks.append(RuleCheck(rule=f"qualification_valid:{qualification.code}", passed=True))

    # Fetch all of the candidate's other assignments once, excluding
    # cancelled ones and the assignment being evaluated (relevant when
    # re-checking someone already in the relief chain).
    other_assignments = [
        a
        for a in candidate.assignments
        if a.id != exclude_assignment_id and a.status != AssignmentStatus.CANCELLED
    ]

    # 5. No overlapping *active* assignment (double-booked right now).
    active_conflicts = [
        a
        for a in other_assignments
        if a.status == AssignmentStatus.ACTIVE
        and overlaps_exclusive(window_start, window_end, a.start_date, _effective_end_date(a))
    ]
    checks.append(
        RuleCheck(
            rule="no_overlapping_assignment",
            passed=not active_conflicts,
            reason=(
                None
                if not active_conflicts
                else f"Already actively assigned to {active_conflicts[0].site.name} "
                f"through {_effective_end_date(active_conflicts[0]).isoformat()}."
            ),
        )
    )

    # 6. No conflicting *planned* future commitment.
    planned_conflicts = [
        a
        for a in other_assignments
        if a.status == AssignmentStatus.PLANNED
        and overlaps_exclusive(window_start, window_end, a.start_date, _effective_end_date(a))
    ]
    checks.append(
        RuleCheck(
            rule="no_conflicting_future_commitment",
            passed=not planned_conflicts,
            reason=(
                None
                if not planned_conflicts
                else f"Already committed to a planned assignment at {planned_conflicts[0].site.name} "
                f"starting {planned_conflicts[0].start_date.isoformat()}."
            ),
        )
    )

    # 7. Rest/rotation rule: the candidate's most recent prior
    # assignment must end at least `minimum_rest_days` before this one
    # starts.
    prior_assignments = [a for a in other_assignments if _effective_end_date(a) <= window_start]
    rest_violation = None
    if prior_assignments:
        most_recent = max(prior_assignments, key=_effective_end_date)
        rest_days = (window_start - _effective_end_date(most_recent)).days
        if rest_days < minimum_rest_days:
            rest_violation = (most_recent, rest_days)
    checks.append(
        RuleCheck(
            rule="rest_rotation_rule",
            passed=rest_violation is None,
            reason=(
                None
                if rest_violation is None
                else f"Only {rest_violation[1]} day(s) of rest since the prior assignment ended "
                f"({minimum_rest_days} required)."
            ),
        )
    )

    return EligibilityResult(
        employee_id=candidate.id,
        employee_name=candidate.full_name,
        role_id=role_id,
        site_id=site_id,
        window_start=window_start,
        window_end=window_end,
        eligible=all(c.passed for c in checks),
        checks=checks,
    )


_CHECK_PHRASES = {
    "active_employment": "is an active employee",
    "role_match": "holds the required role",
    "availability_status": "is available for the assignment period",
    "no_overlapping_assignment": "has no overlapping assignment",
    "no_conflicting_future_commitment": "has no conflicting future commitment",
    "rest_rotation_rule": "satisfies the minimum rest requirement",
}


def format_eligibility_summary(result: EligibilityResult) -> str:
    """Render an EligibilityResult as a plain-English sentence.

    This is deterministic string formatting over already-decided
    facts, not an AI-generated explanation - it exists so the frontend
    (and, later, an AI assistant) has a ready-made, always-accurate
    summary instead of re-deriving one from the raw checks.
    """
    if not result.eligible:
        first_failure = result.failed_checks[0]
        return f"{result.employee_name} is not eligible: {first_failure.reason}"

    phrases = [_CHECK_PHRASES[c.rule] for c in result.checks if c.rule in _CHECK_PHRASES]
    if any(c.rule.startswith("qualification_valid:") for c in result.checks):
        phrases.append("has all mandatory qualifications valid through the assignment end date")

    if len(phrases) == 1:
        return f"{result.employee_name} {phrases[0]}."
    return f"{result.employee_name} " + ", ".join(phrases[:-1]) + f", and {phrases[-1]}."
