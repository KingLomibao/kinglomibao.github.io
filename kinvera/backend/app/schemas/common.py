"""
API-facing (Pydantic) schemas for the eligibility engine's structured
results.

These mirror the dataclasses in app/domain/results.py, but are a
separate layer on purpose: the domain layer's job is to be correct
Python for the rest of the backend to call, while these schemas' job
is to be a stable, versioned JSON contract for the frontend (and,
later, the AI tool layer). Keeping them separate means a change to one
doesn't automatically ripple into the other.
"""

from datetime import date

from pydantic import BaseModel

from app.domain.eligibility import format_eligibility_summary
from app.domain.results import EligibilityResult, RuleCheck


class RuleCheckSchema(BaseModel):
    rule: str
    passed: bool
    reason: str | None = None

    @classmethod
    def from_domain(cls, check: RuleCheck) -> "RuleCheckSchema":
        return cls(rule=check.rule, passed=check.passed, reason=check.reason)


class EligibilityResultSchema(BaseModel):
    employee_id: int
    employee_name: str
    role_id: int
    site_id: int
    window_start: date
    window_end: date
    eligible: bool
    checks: list[RuleCheckSchema]
    summary: str

    @classmethod
    def from_domain(cls, result: EligibilityResult) -> "EligibilityResultSchema":
        return cls(
            employee_id=result.employee_id,
            employee_name=result.employee_name,
            role_id=result.role_id,
            site_id=result.site_id,
            window_start=result.window_start,
            window_end=result.window_end,
            eligible=result.eligible,
            checks=[RuleCheckSchema.from_domain(c) for c in result.checks],
            summary=format_eligibility_summary(result),
        )
