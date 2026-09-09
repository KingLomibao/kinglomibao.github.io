from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AssignmentStatus, pg_enum

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role import Role
    from app.models.site import Site


class Assignment(Base):
    """An employee deployed to a site under a role for a date window.

    `planned_end_date` is the scheduled end of the deployment;
    `actual_end_date` is filled in only once the assignment truly ends
    (it may differ from the plan, e.g. after an extension).

    `relieving_assignment_id` is what lets the system answer "who is
    planned to relieve whom": it points from a reliever's assignment
    back to the assignment it is scheduled to relieve. This is the
    same field the relief-due and extension-simulation logic use to
    walk the relief chain.
    """

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    start_date: Mapped[date] = mapped_column(nullable=False)
    planned_end_date: Mapped[date] = mapped_column(nullable=False)
    actual_end_date: Mapped[date | None] = mapped_column(nullable=True)

    status: Mapped[AssignmentStatus] = mapped_column(
        pg_enum(AssignmentStatus, "assignment_status"), nullable=False
    )

    relieving_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignments.id"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(String(300))

    employee: Mapped["Employee"] = relationship(back_populates="assignments", foreign_keys=[employee_id])
    site: Mapped["Site"] = relationship(back_populates="assignments")
    role: Mapped["Role"] = relationship()

    relieves: Mapped["Assignment | None"] = relationship(
        remote_side=[id], foreign_keys=[relieving_assignment_id]
    )

    def __repr__(self) -> str:
        return (
            f"Assignment(id={self.id}, employee_id={self.employee_id}, "
            f"site_id={self.site_id}, status={self.status})"
        )
