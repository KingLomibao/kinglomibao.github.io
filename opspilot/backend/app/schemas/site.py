from pydantic import BaseModel

from app.domain.results import StaffingCoverageItem
from app.models import Site


class SiteSchema(BaseModel):
    id: int
    code: str
    name: str
    location: str
    status: str

    @classmethod
    def from_orm_site(cls, site: Site) -> "SiteSchema":
        return cls(id=site.id, code=site.code, name=site.name, location=site.location, status=site.status.value)


class StaffingCoverageSchema(BaseModel):
    site_id: int
    site_name: str
    role_id: int
    role_name: str
    minimum_required: int
    currently_assigned: int
    shortage: int
    status: str

    @classmethod
    def from_domain(cls, item: StaffingCoverageItem) -> "StaffingCoverageSchema":
        return cls(
            site_id=item.site_id,
            site_name=item.site_name,
            role_id=item.role_id,
            role_name=item.role_name,
            minimum_required=item.minimum_required,
            currently_assigned=item.currently_assigned,
            shortage=item.shortage,
            status=item.status,
        )
