from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.site import Site


class SiteStaffingRequirement(Base):
    """Minimum number of employees of a given role required at a site.

    This is deliberately simple (a single number per site+role) rather
    than a scheduling/optimization model. It is enough for the
    staffing-coverage view and the extension-simulation engine to
    determine, deterministically, whether a proposed change would drop
    a site below the minimum headcount it needs for a role.
    """

    __tablename__ = "site_staffing_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    minimum_required: Mapped[int] = mapped_column(Integer, nullable=False)

    site: Mapped["Site"] = relationship(back_populates="staffing_requirements")
    role: Mapped["Role"] = relationship()

    def __repr__(self) -> str:
        return (
            f"SiteStaffingRequirement(site_id={self.site_id}, role_id={self.role_id}, "
            f"minimum_required={self.minimum_required})"
        )
