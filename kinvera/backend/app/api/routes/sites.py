from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.staffing import get_staffing_coverage
from app.models import Site
from app.schemas.site import SiteSchema, StaffingCoverageSchema

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("", response_model=list[SiteSchema])
def list_sites(db: Session = Depends(get_db)) -> list[SiteSchema]:
    sites = db.query(Site).order_by(Site.name).all()
    return [SiteSchema.from_orm_site(s) for s in sites]


@router.get("/{site_id}", response_model=SiteSchema)
def read_site(site_id: int, db: Session = Depends(get_db)) -> SiteSchema:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return SiteSchema.from_orm_site(site)


@router.get("/{site_id}/staffing-coverage", response_model=list[StaffingCoverageSchema])
def read_site_staffing_coverage(site_id: int, db: Session = Depends(get_db)) -> list[StaffingCoverageSchema]:
    coverage = get_staffing_coverage(db, site_id=site_id)
    return [StaffingCoverageSchema.from_domain(c) for c in coverage]
