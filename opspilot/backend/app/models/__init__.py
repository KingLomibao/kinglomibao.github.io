"""
ORM models package.

Every model module is imported here so that (a) SQLAlchemy can resolve
the string-based relationship references between them (e.g.
Employee.assignments -> "Assignment"), and (b) Alembic's autogenerate
can see the full set of tables when comparing against the database.
"""

from app.models.assignment import Assignment
from app.models.employee import Employee
from app.models.qualification import EmployeeQualification, Qualification, RoleQualificationRequirement
from app.models.role import Role
from app.models.site import Site
from app.models.staffing_requirement import SiteStaffingRequirement
from app.models.workforce_movement import WorkforceMovement

__all__ = [
    "Assignment",
    "Employee",
    "EmployeeQualification",
    "Qualification",
    "Role",
    "RoleQualificationRequirement",
    "Site",
    "SiteStaffingRequirement",
    "WorkforceMovement",
]
