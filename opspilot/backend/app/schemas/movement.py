from datetime import date

from pydantic import BaseModel

from app.models import WorkforceMovement


class WorkforceMovementSchema(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    movement_type: str
    movement_date: date
    from_site_id: int | None
    from_site_name: str | None
    to_site_id: int | None
    to_site_name: str | None
    notes: str | None

    @classmethod
    def from_orm_movement(cls, movement: WorkforceMovement) -> "WorkforceMovementSchema":
        return cls(
            id=movement.id,
            employee_id=movement.employee_id,
            employee_name=movement.employee.full_name,
            movement_type=movement.movement_type.value,
            movement_date=movement.movement_date,
            from_site_id=movement.from_site_id,
            from_site_name=movement.from_site.name if movement.from_site else None,
            to_site_id=movement.to_site_id,
            to_site_name=movement.to_site.name if movement.to_site else None,
            notes=movement.notes,
        )
