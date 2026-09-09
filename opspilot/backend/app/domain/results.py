"""
Structured result types returned by the domain/business-rule layer.

These are plain dataclasses, not database models and not API schemas.
They exist so every rule function - eligibility, relief-due, staffing,
simulation - returns the same kind of self-explanatory, structured
object instead of a bare boolean or a raw ORM row. The API layer wraps
these in Pydantic schemas for JSON responses; a future AI layer would
receive exactly these same structures to explain to a user, which is
the whole point of keeping "what happened" (this file) separate from
"how it's decided" (eligibility.py, staffing.py, simulation.py) and
"how it's decided" separate from "how it's phrased" (the LLM, later).
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RuleCheck:
    """The outcome of a single, named business rule check."""

    rule: str
    passed: bool
    reason: str | None = None


@dataclass
class EligibilityResult:
    """Whether one candidate employee is eligible for one assignment
    window, and exactly which rule(s) drove that conclusion."""

    employee_id: int
    employee_name: str
    role_id: int
    site_id: int
    window_start: date
    window_end: date
    eligible: bool
    checks: list[RuleCheck] = field(default_factory=list)

    @property
    def failed_checks(self) -> list[RuleCheck]:
        return [c for c in self.checks if not c.passed]


@dataclass
class ReliefDueItem:
    """One active assignment whose planned end falls inside the
    relief-due window, with whatever relief is already lined up."""

    assignment_id: int
    employee_id: int
    employee_name: str
    role_id: int
    role_name: str
    site_id: int
    site_name: str
    planned_end_date: date
    days_remaining: int
    reliever_employee_id: int | None
    reliever_employee_name: str | None
    reliever_assignment_id: int | None
    reliever_status: str  # "planned" | "none"
    risk: str  # "no_reliever" | "reliever_planned" | "overdue"


@dataclass
class StaffingCoverageItem:
    """Minimum-required vs. currently-assigned headcount for one
    site+role combination."""

    site_id: int
    site_name: str
    role_id: int
    role_name: str
    minimum_required: int
    currently_assigned: int

    @property
    def shortage(self) -> int:
        return max(0, self.minimum_required - self.currently_assigned)

    @property
    def status(self) -> str:
        return "short" if self.shortage > 0 else "meeting"


@dataclass
class DashboardSummary:
    """Top-line KPIs for the main dashboard - each number is a direct
    count from the database, computed by the same domain functions
    that back their dedicated views (nothing here is a separate,
    parallel calculation)."""

    total_active_workforce: int
    currently_assigned: int
    available: int
    on_leave: int
    unavailable: int
    relief_due_in_window: int
    relief_window_days: int
    qualification_risks: int
    staffing_shortages: int
    total_sites: int


@dataclass
class ImpactEvent:
    """One node in the downstream impact graph produced by the
    extension-simulation engine, e.g. 'reliever's next assignment now
    conflicts' or 'site drops below minimum staffing'."""

    category: str
    description: str
    severity: str  # "info" | "low" | "medium" | "high"
    employee_id: int | None = None
    assignment_id: int | None = None
    site_id: int | None = None


@dataclass
class ExtensionSimulationResult:
    """The full, non-destructive result of simulating an assignment
    extension: what would change, what it collides with downstream,
    and who could realistically absorb the gap."""

    assignment_id: int
    employee_id: int
    employee_name: str
    extension_days: int
    original_planned_end_date: date
    simulated_planned_end_date: date
    events: list[ImpactEvent] = field(default_factory=list)
    staffing_impacts: list[StaffingCoverageItem] = field(default_factory=list)
    eligible_alternatives: list[EligibilityResult] = field(default_factory=list)
    rejected_alternatives: list[EligibilityResult] = field(default_factory=list)

    @property
    def has_conflict(self) -> bool:
        return any(e.severity in ("medium", "high") for e in self.events)

    @property
    def overall_severity(self) -> str:
        severities = [e.severity for e in self.events]
        for level in ("high", "medium", "low"):
            if level in severities:
                return level
        return "info"
