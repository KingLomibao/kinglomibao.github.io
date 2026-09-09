from datetime import date

from pydantic import BaseModel

from app.domain.results import ReliefDueItem


class ReliefDueItemSchema(BaseModel):
    assignment_id: int
    employee_id: int
    employee_name: str
    role_id: int
    role_name: str
    site_id: int
    site_name: str
    planned_end_date: date
    days_remaining: int
    reliever_employee_id: int | None
    reliever_employee_name: str | None
    reliever_assignment_id: int | None
    reliever_status: str
    risk: str

    @classmethod
    def from_domain(cls, item: ReliefDueItem) -> "ReliefDueItemSchema":
        return cls(**item.__dict__)
