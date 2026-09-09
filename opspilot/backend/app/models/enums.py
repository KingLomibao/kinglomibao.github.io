"""
Shared enumerations used across the data model.

Using Python enums (mapped to native PostgreSQL ENUM types by
SQLAlchemy) instead of free-text strings means invalid statuses like
"asigned" (typo) are rejected at the database level, and every place in
the codebase that checks a status is checking against the same fixed
set of values instead of a "magic string".
"""

import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Build a Postgres ENUM column type that stores lowercase values.

    Without `values_callable`, SQLAlchemy stores an enum member's
    *name* (e.g. "ACTIVE") rather than its *value* (e.g. "active").
    Our Python code, JSON API responses, and this file's own value
    strings should all agree, so every enum column in the schema is
    built through this one helper.
    """
    return SAEnum(enum_cls, name=name, values_callable=lambda obj: [e.value for e in obj])


class RoleCategory(str, enum.Enum):
    TECHNICAL = "technical"
    SUPERVISORY = "supervisory"


class SiteStatus(str, enum.Enum):
    ACTIVE = "active"
    DEMOBILIZING = "demobilizing"
    INACTIVE = "inactive"


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class AvailabilityStatus(str, enum.Enum):
    """Describes an employee's availability when NOT currently assigned.

    Whether someone is *currently assigned* is derived from the
    Assignment table (source of truth), not this field. This field
    captures the *reason* an employee is or isn't available for a new
    assignment: resting between rotations, on approved leave, assigned
    to a site already, or otherwise unavailable (e.g. medical hold).
    """

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    ON_LEAVE = "on_leave"
    UNAVAILABLE = "unavailable"


class AssignmentStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MovementType(str, enum.Enum):
    MOBILIZATION = "mobilization"
    DEMOBILIZATION = "demobilization"
    ROTATION_OUT = "rotation_out"
    ROTATION_IN = "rotation_in"
    RELIEF_IN = "relief_in"
    RELIEF_OUT = "relief_out"
