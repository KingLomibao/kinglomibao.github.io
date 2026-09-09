"""
Resolving a plain-language name into a specific Employee row.

Every AI tool that takes a person's name (nearly all of them) goes
through `resolve_employee_by_name` so ambiguous or unknown names are
handled exactly once, the same way everywhere: never by silently
guessing. This is what backs the "ask for clarification" requirement
for the AI assistant - the tool layer refuses to pick a name for the
LLM, so the LLM can never be tempted to either.
"""

from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.domain.employee_view import current_assignment
from app.models import Employee
from app.models.enums import EmploymentStatus


@dataclass
class EmployeeMatch:
    id: int
    full_name: str
    role_name: str
    site_name: str | None


def _to_match(employee: Employee) -> EmployeeMatch:
    assignment = current_assignment(employee)
    return EmployeeMatch(
        id=employee.id,
        full_name=employee.full_name,
        role_name=employee.role.name,
        site_name=assignment.site.name if assignment else None,
    )


class EmployeeNotFoundError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"No employee found matching '{name}'.")


class AmbiguousEmployeeError(Exception):
    """Raised when a name matches more than one employee. Carries
    enough distinguishing detail (id, role, site) for the caller to
    ask the user which one they meant, per the product requirement
    that the assistant never silently guesses."""

    def __init__(self, name: str, matches: list[EmployeeMatch]):
        self.name = name
        self.matches = matches
        super().__init__(f"'{name}' matches {len(matches)} employees.")


def resolve_employee_by_name(db: Session, name: str) -> Employee:
    """Find exactly one active employee by full, first, or last name.

    Reuses the same matching approach as the employee search API route
    (first/last/full name, case-insensitive) rather than inventing a
    second way to search for a person.
    """
    pattern = f"%{name.strip()}%"
    full_name = func.concat(Employee.first_name, " ", Employee.last_name)
    matches = (
        db.query(Employee)
        .filter(Employee.employment_status == EmploymentStatus.ACTIVE)
        .filter(or_(Employee.first_name.ilike(pattern), Employee.last_name.ilike(pattern), full_name.ilike(pattern)))
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )

    if not matches:
        raise EmployeeNotFoundError(name)

    # An exact full-name match (case-insensitive) disambiguates even
    # when a partial search would have returned several employees -
    # e.g. searching "Smith" matches several people, but "John Smith"
    # should resolve directly to the one employee with that exact name.
    exact = [e for e in matches if e.full_name.lower() == name.strip().lower()]
    if len(exact) == 1:
        return exact[0]

    if len(matches) > 1:
        raise AmbiguousEmployeeError(name, [_to_match(e) for e in matches])

    return matches[0]
