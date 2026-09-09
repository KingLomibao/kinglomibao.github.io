from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role import Role


class Qualification(Base):
    """A certification or training an employee can hold.

    e.g. "Working at Height Certification". Qualifications are defined
    once here, and linked to specific employees (with issue/expiry
    dates) via EmployeeQualification, and to roles (mandatory or not)
    via RoleQualificationRequirement.
    """

    __tablename__ = "qualifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))

    employee_qualifications: Mapped[list["EmployeeQualification"]] = relationship(
        back_populates="qualification"
    )
    role_requirements: Mapped[list["RoleQualificationRequirement"]] = relationship(
        back_populates="qualification"
    )

    def __repr__(self) -> str:
        return f"Qualification(id={self.id}, code={self.code!r})"


class RoleQualificationRequirement(Base):
    """Defines which qualifications are mandatory for a given role.

    This is the table the eligibility engine consults to know *which*
    qualifications it must check for a candidate being evaluated for a
    given role - the requirement is never hard-coded in business-rule
    code or in the frontend.
    """

    __tablename__ = "role_qualification_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    qualification_id: Mapped[int] = mapped_column(ForeignKey("qualifications.id"), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped["Role"] = relationship(back_populates="qualification_requirements")
    qualification: Mapped["Qualification"] = relationship(back_populates="role_requirements")

    def __repr__(self) -> str:
        return (
            f"RoleQualificationRequirement(role_id={self.role_id}, "
            f"qualification_id={self.qualification_id})"
        )


class EmployeeQualification(Base):
    """A specific qualification held by a specific employee.

    `expiry_date` is what the eligibility engine and the "Qualification
    Risks" dashboard widget compare against assignment windows and the
    current date - validity is always derived from these dates, never
    stored as a separate boolean that could drift out of sync.
    """

    __tablename__ = "employee_qualifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    qualification_id: Mapped[int] = mapped_column(ForeignKey("qualifications.id"), nullable=False)
    issue_date: Mapped[date] = mapped_column(nullable=False)
    expiry_date: Mapped[date] = mapped_column(nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="qualifications")
    qualification: Mapped["Qualification"] = relationship(back_populates="employee_qualifications")

    def __repr__(self) -> str:
        return (
            f"EmployeeQualification(employee_id={self.employee_id}, "
            f"qualification_id={self.qualification_id}, expiry_date={self.expiry_date})"
        )

