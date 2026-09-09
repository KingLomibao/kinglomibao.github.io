from datetime import date

from pydantic import BaseModel

from app.domain.replacement import ReplacementSearchResult
from app.schemas.common import EligibilityResultSchema


class ReplacementSearchResponseSchema(BaseModel):
    target_assignment_id: int
    target_employee_id: int
    target_employee_name: str
    role_id: int
    role_name: str
    site_id: int
    site_name: str
    window_start: date
    window_end: date
    eligible_candidates: list[EligibilityResultSchema]
    rejected_candidates: list[EligibilityResultSchema]

    @classmethod
    def from_domain(cls, result: ReplacementSearchResult) -> "ReplacementSearchResponseSchema":
        return cls(
            target_assignment_id=result.target_assignment_id,
            target_employee_id=result.target_employee_id,
            target_employee_name=result.target_employee_name,
            role_id=result.role_id,
            role_name=result.role_name,
            site_id=result.site_id,
            site_name=result.site_name,
            window_start=result.window_start,
            window_end=result.window_end,
            eligible_candidates=[EligibilityResultSchema.from_domain(c) for c in result.eligible_candidates],
            rejected_candidates=[EligibilityResultSchema.from_domain(c) for c in result.rejected_candidates],
        )
