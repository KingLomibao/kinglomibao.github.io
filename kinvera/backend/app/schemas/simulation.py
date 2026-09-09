from datetime import date

from pydantic import BaseModel, Field

from app.domain.results import ExtensionSimulationResult, ImpactEvent
from app.schemas.common import EligibilityResultSchema
from app.schemas.site import StaffingCoverageSchema


class ExtensionSimulationRequestSchema(BaseModel):
    extension_days: int = Field(..., description="Number of days to add to the assignment's planned end date.")


class ImpactEventSchema(BaseModel):
    category: str
    description: str
    severity: str
    employee_id: int | None = None
    assignment_id: int | None = None
    site_id: int | None = None

    @classmethod
    def from_domain(cls, event: ImpactEvent) -> "ImpactEventSchema":
        return cls(**event.__dict__)


class ExtensionSimulationResponseSchema(BaseModel):
    assignment_id: int
    employee_id: int
    employee_name: str
    extension_days: int
    original_planned_end_date: date
    simulated_planned_end_date: date
    is_destructive: bool = Field(
        default=False,
        description="Always false in Phase 1 - this is a preview only; no records are modified.",
    )
    overall_severity: str
    events: list[ImpactEventSchema]
    staffing_impacts: list[StaffingCoverageSchema]
    eligible_alternatives: list[EligibilityResultSchema]
    rejected_alternatives: list[EligibilityResultSchema]

    @classmethod
    def from_domain(cls, result: ExtensionSimulationResult) -> "ExtensionSimulationResponseSchema":
        return cls(
            assignment_id=result.assignment_id,
            employee_id=result.employee_id,
            employee_name=result.employee_name,
            extension_days=result.extension_days,
            original_planned_end_date=result.original_planned_end_date,
            simulated_planned_end_date=result.simulated_planned_end_date,
            overall_severity=result.overall_severity,
            events=[ImpactEventSchema.from_domain(e) for e in result.events],
            staffing_impacts=[StaffingCoverageSchema.from_domain(s) for s in result.staffing_impacts],
            eligible_alternatives=[EligibilityResultSchema.from_domain(c) for c in result.eligible_alternatives],
            rejected_alternatives=[EligibilityResultSchema.from_domain(c) for c in result.rejected_alternatives],
        )
