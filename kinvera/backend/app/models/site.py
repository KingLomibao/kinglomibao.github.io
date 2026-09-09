from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SiteStatus, pg_enum

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.staffing_requirement import SiteStaffingRequirement


class Site(Base):
    """A client site or project where employees are deployed.

    In a real deployment this might represent a plant, a facility, a
    construction project, or any other place work happens. Phase 1
    treats "site" and "project" as the same concept for simplicity.
    """

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[SiteStatus] = mapped_column(pg_enum(SiteStatus, "site_status"), nullable=False)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="site")
    staffing_requirements: Mapped[list["SiteStaffingRequirement"]] = relationship(
        back_populates="site"
    )

    def __repr__(self) -> str:
        return f"Site(id={self.id}, code={self.code!r})"
