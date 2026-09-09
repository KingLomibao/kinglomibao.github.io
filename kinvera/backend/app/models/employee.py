from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AvailabilityStatus, EmploymentStatus, pg_enum

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.qualification import EmployeeQualification
    from app.models.role import Role


class Employee(Base):
    """A person who can be deployed to a site under a role.

    `employment_status` says whether the person is employed by the
    company at all. `availability_status` explains *why* someone is or
    isn't free for a new assignment when they have no current
    assignment (resting, on leave, or otherwise unavailable). Whether
    someone is *currently assigned right now* is always derived from
    the Assignment table, never from a stored flag here, so the two
    can never silently disagree.
    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        pg_enum(EmploymentStatus, "employment_status"), nullable=False
    )
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        pg_enum(AvailabilityStatus, "availability_status"), nullable=False
    )
    home_location: Mapped[str | None] = mapped_column(String(150))
    hire_date: Mapped[date] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped["Role"] = relationship(back_populates="employees")
    qualifications: Mapped[list["EmployeeQualification"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="employee",
        foreign_keys="Assignment.employee_id",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"Employee(id={self.id}, employee_number={self.employee_number!r})"
