from pydantic import BaseModel

from app.domain.results import DashboardSummary


class DashboardSummarySchema(BaseModel):
    total_active_workforce: int
    currently_assigned: int
    available: int
    on_leave: int
    unavailable: int
    relief_due_in_window: int
    relief_window_days: int
    qualification_risks: int
    staffing_shortages: int
    total_sites: int

    @classmethod
    def from_domain(cls, summary: DashboardSummary) -> "DashboardSummarySchema":
        return cls(**summary.__dict__)
