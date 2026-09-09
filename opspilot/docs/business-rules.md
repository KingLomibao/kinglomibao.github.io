# Business Rules

Every rule below is implemented in `backend/app/domain/` and covered by
tests in `tests/backend/`. This document exists so anyone inspecting
the repository can understand exactly why an employee is considered
eligible or ineligible, without reading the code - and so an AI layer
added later can never claim a rule the code doesn't actually enforce.

> **AI explains. Business rules decide.** Nothing in this document is
> evaluated by a language model. It is ordinary Python comparing dates,
> statuses, and foreign keys.

## 1. Replacement eligibility

**Function:** `evaluate_replacement_eligibility()` in `app/domain/eligibility.py`

Given a candidate employee and a required (role, site, date window),
the engine runs seven independent checks and returns a structured
result - never a bare `true`/`false`:

```json
{
  "employee_id": 42,
  "employee_name": "Ahmed Rahman",
  "eligible": false,
  "checks": [
    { "rule": "active_employment", "passed": true },
    { "rule": "role_match", "passed": true },
    { "rule": "availability_status", "passed": true },
    { "rule": "qualification_valid:WORK_HEIGHT", "passed": false,
      "reason": "Working at Height Certification expires 2026-08-30, before the assignment ends 2026-10-23." },
    { "rule": "no_overlapping_assignment", "passed": true },
    { "rule": "no_conflicting_future_commitment", "passed": true },
    { "rule": "rest_rotation_rule", "passed": true }
  ]
}
```

An employee is **eligible only if every check passes.**

| # | Rule | What it checks | Where it can fail |
|---|---|---|---|
| 1 | `active_employment` | `employee.active` is true and `employment_status == active` | Terminated or deactivated employees |
| 2 | `role_match` | The candidate's role matches the role the assignment requires | Phase 1 only supports an exact match - see [Limitations](#limitations) |
| 3 | `availability_status` | The candidate isn't currently marked `on_leave` or `unavailable` | An approximation of "available for the window" - see [Limitations](#limitations) |
| 4 | `qualification_valid:<CODE>` | One check per qualification the role mandates (`role_qualification_requirements`): the candidate has that qualification on file, with `expiry_date >= window_end` | Missing entirely, or expires before the assignment ends |
| 5 | `no_overlapping_assignment` | No other **active** assignment overlaps the required window | Double-booked at another site right now |
| 6 | `no_conflicting_future_commitment` | No other **planned** assignment overlaps the required window | Already promised to relieve someone else during this window |
| 7 | `rest_rotation_rule` | At least `MINIMUM_REST_DAYS` (default 2, configurable) between the end of the candidate's most recent prior assignment and the start of this one | Coming straight off one assignment into another with no rest |

Overlap is checked with same-day handovers allowed: an assignment
ending on day X and another starting on day X is a normal relief
handover, not a conflict.

## 2. Relief-due lookup

**Function:** `get_relief_due()` in `app/domain/relief.py`

"Who needs relief in the next N days?" - `N` is a parameter
(`window_days`), defaulting to `DEFAULT_RELIEF_WINDOW_DAYS` (30,
configurable via environment variable), never hard-coded.

- Only assignments with `status == active` are considered. A `completed` assignment never appears here, even if its planned end date falls inside the window.
- An assignment is included if `planned_end_date <= today + window_days`.
- If `planned_end_date` has already passed and the assignment is still `active`, it is flagged `risk: "overdue"` - relief did not happen on schedule.
- The reliever, if any, is found by looking for another assignment whose `relieving_assignment_id` points at this one. If none exists, `risk: "no_reliever"`.

## 3. Staffing coverage

**Functions:** `get_staffing_coverage()`, `get_staffing_shortages()`, `count_role_coverage()` in `app/domain/staffing.py`

`site_staffing_requirements` defines the minimum headcount of a role a
site needs. Coverage is the count of `active` assignments at that
site+role. A site is **short-staffed** whenever
`currently_assigned < minimum_required`. This is a single number per
site+role, by design - Phase 1 is not a scheduling optimizer.

`count_role_coverage()` is the same idea generalized to an arbitrary
future date window (rather than "as of today"), which is what the
extension-simulation engine uses to check whether a *proposed* change
would create a gap.

## 4. Replacement search ("who can replace X?")

**Function:** `find_replacement_candidates()` in `app/domain/replacement.py`

1. Load the target assignment.
2. The required window is `[max(assignment.start_date, today), assignment.planned_end_date]` - "if this person had to be replaced starting now, who could cover the rest of this assignment?"
3. Candidates are every *other*, active employee holding the same role.
4. Every candidate is run through `evaluate_replacement_eligibility()` - the exact function described in section 1.
5. The result separates `eligible_candidates` from `rejected_candidates`, each carrying full rule-by-rule evidence, so rejections are auditable rather than silent.

A ready-made plain-language summary (`format_eligibility_summary()`)
is deterministically formatted from the same checks - e.g. *"Ahmed
Rahman holds the required role, is available for the assignment
period, has all mandatory qualifications valid through the assignment
end date, and has no conflicting assignment."* This is string
formatting over already-decided facts, not an AI-generated
explanation.

## 5. Assignment-extension impact simulation

**Function:** `simulate_extension()` in `app/domain/simulation.py`

Answers "what happens if this assignment runs N more days?" as a
**non-destructive preview** - it never writes the new end date (or
anything else) to the database. See
[architecture.md](./architecture.md#extension-simulation-engine) for
how it walks the relief chain. Concretely, it:

1. Computes `simulated_end = target.planned_end_date + extension_days` (locally only).
2. Finds the assignment's direct reliever (`relieving_assignment_id == target.id`), if any. No reliever -> no downstream conflict, done.
3. If the reliever's original start date is now before `simulated_end`, they're delayed by the difference.
4. Shifts the reliever's own window forward by that same delay (keeping their original duration) and checks it against the reliever's *other* commitments for an overlap.
5. If an overlap is found, that commitment (and whoever *it* was going to relieve) loses expected coverage for the delay period.
6. Checks `site_staffing_requirements` for that site+role during the gap - if coverage drops below the minimum, a staffing-shortage event is raised.
7. Searches for alternative candidates to cover the gap using the **exact same** `evaluate_replacement_eligibility()` function from section 1 - never a separate, simulation-only notion of eligible.

The response's `is_destructive` field is always `false` in Phase 1;
the frontend labels these results "deterministic operational impact
analysis," never as an AI prediction.

## Seeded demonstration scenario

The synthetic dataset (`backend/app/seed/scenario.py`) hand-builds one
fully deterministic chain so the simulation above always has something
real to show:

| Employee | Assignment | Site | Window | Notes |
|---|---|---|---|---|
| **John Smith** | active | Northfield Compression Station | now -> +16 days | The assignment being extended |
| **Ahmed Rahman** | planned, relieves John | Northfield Compression Station | +16d -> +30d | 14-day relief swing |
| **Ahmed Rahman** | planned, relieves Priya | Meridian Solar Array | +30d -> +75d | Already committed here right after |
| **Priya Nair** | active | Meridian Solar Array | now -> +30d | Expects Ahmed on day +30 |
| **Diego Alvarez** | none (bench) | - | - | Fully qualified alternative -> **eligible** |
| **Grace Kim** | none (bench) | - | - | Working at Height already expired -> **ineligible** |
| **Marcus Webb** | none (bench) | - | - | Working at Height expires mid-gap -> **ineligible** |

Running **"extend John Smith's assignment by 14 days"** produces:

1. `reliever_affected` - Ahmed's relief of John is delayed 14 days (to +30d, matching the new end date).
2. `reliever_next_assignment_conflict` - Ahmed's shifted window at Northfield (+30d -> +44d) now overlaps his already-planned relief of Priya at Meridian Solar Array (starting +30d).
3. `downstream_coverage_loss` - Meridian Solar Array expected Ahmed on day +30 and won't get him until +44.
4. `staffing_shortage` - Meridian Solar Array requires 1 Senior Field Technician and would have 0 from +30d to +44d (the site's staffing minimum is deliberately met *only* by Priya, so nothing else covers the gap - see `SCENARIO_RESERVED_SLOTS` in `generate_synthetic_data.py`).
5. Alternatives for that gap are searched with the standard eligibility engine: **Diego Alvarez is eligible; Grace Kim and Marcus Webb are rejected**, both specifically on the `qualification_valid:WORK_HEIGHT` rule - proving the qualification date, not availability, is what limits the alternatives.

This exact scenario is asserted in
`tests/backend/test_simulation.py::test_john_smith_extension_scenario`
(built independently via test factories, so it doesn't depend on the
seed script's random ordering).

## Limitations

Documented here rather than hidden, per the project's own principle
that AI (and this document) should never claim more certainty than the
underlying data supports:

- **Role match is exact-only.** Phase 1 has no notion of one role being an acceptable substitute for another (e.g. a Site Supervisor covering a Senior Field Technician gap). That would be modeled as data (a role-substitution table), not a special case in code.
- **"Available for the window" is a snapshot, not a calendar.** `availability_status` is a single current value per employee, not a set of dated leave records, so the engine cannot yet tell that someone marked `on_leave` today will be back in three days. A future phase would add a leave-period table and check it against the specific window instead.
- **The simulation walks one relief hop.** It follows target -> reliever -> reliever's next commitment -> whoever that commitment relieves, and stops there. A deeper chain (that commitment's own downstream effects) is a natural, additive extension, not something Phase 1 claims to model.
- **Staffing minimums are a single number per site+role.** There's no time-of-day, shift pattern, or skill-mix optimization - deliberately, to keep the rule easy to audit.
