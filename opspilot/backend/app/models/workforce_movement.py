from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MovementType, pg_enum

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.employee import Employee
    from app.models.site import Site


class WorkforceMovement(Base):
    """A discrete, dated event describing workforce movement.

    Assignments describe *periods* of deployment; a WorkforceMovement
    records the *events* around them (mobilizing to a site, rotating
    out, being relieved, etc.) so the "Upcoming Movements" view has a
    clean, chronological feed to render instead of having to infer
    events from assignment start/end dates.
    """

    __tablename__ = "workforce_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(
        pg_enum(MovementType, "movement_type"), nullable=False
    )
    movement_date: Mapped[date] = mapped_column(nullable=False)
    from_site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True)
    to_site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(300))

    employee: Mapped["Employee"] = relationship()
    assignment: Mapped["Assignment"] = relationship()
    from_site: Mapped["Site | None"] = relationship(foreign_keys=[from_site_id])
    to_site: Mapped["Site | None"] = relationship(foreign_keys=[to_site_id])

    def __repr__(self) -> str:
        return f"WorkforceMovement(id={self.id}, type={self.movement_type})"
