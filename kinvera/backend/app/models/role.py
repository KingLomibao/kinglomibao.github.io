from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoleCategory, pg_enum

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.qualification import RoleQualificationRequirement


class Role(Base):
    """A job function an employee can hold, e.g. 'Site Supervisor'.

    Roles drive two other parts of the data model: which qualifications
    are mandatory (RoleQualificationRequirement) and how many people of
    that role a site needs (SiteStaffingRequirement).
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[RoleCategory] = mapped_column(
        pg_enum(RoleCategory, "role_category"), nullable=False
    )

    employees: Mapped[list["Employee"]] = relationship(back_populates="role")
    qualification_requirements: Mapped[list["RoleQualificationRequirement"]] = relationship(
        back_populates="role"
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id}, code={self.code!r})"
