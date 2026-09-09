# Kinvera

**AI-ready Workforce Operations Platform**

A portfolio project demonstrating a deterministic workforce-operations
backend and dashboard for a fictional field-services company, with a
grounded AI operations assistant built on top of it that never makes
an operational decision itself.

> All company names, employees, sites, and data in this project are
> synthetic. Kinvera is not affiliated with any real organization.

## Design Principle

> **AI explains. Business rules decide.**
>
> The AI Operations Assistant never independently determines workforce
> eligibility, qualification compliance, availability, staffing
> sufficiency, or operational conflicts. Those conclusions come from
> deterministic backend logic operating on structured database
> records. The AI layer only calls trusted backend tools and explains
> their results in plain language.

## The Problem

Workforce planning in field-services, industrial, and project-based
operations is often fragmented across spreadsheets, emails, phone
calls, and the individual operational knowledge of a handful of
schedulers. Questions like *"who needs relief soon?"*, *"who can
replace this person?"*, and *"what happens if we extend someone's
assignment?"* get answered from memory and gut feel, and the reasoning
behind the answer usually isn't written down anywhere.

## The Solution

Kinvera combines:

- **Structured workforce data** - employees, roles, sites, qualifications, assignments, and movements in a normalized PostgreSQL schema.
- **Deterministic business rules** - a reusable eligibility engine, relief-due logic, and staffing-coverage checks that return rule-by-rule evidence, not just a yes/no.
- **Scenario simulation** - a non-destructive "what happens if this assignment runs N days longer?" tool that traces the real downstream conflict through the relief chain.
- **A grounded AI Operations Assistant** - every rule above is exposed as a plain function, a REST endpoint, and now an AI tool, so the assistant calls them and explains the results rather than reasoning about eligibility itself.

## The Company

**Ironbridge Field Operations** is a fictional field-services company
running ~250 technical and supervisory staff across 10 operational
sites - compression stations, solar and wind installations, water
treatment, rail and logistics depots, telecom and data-center
facilities, a petrochemical plant, and a demobilizing mine-support
site. The synthetic dataset deliberately includes staffing shortages,
expired/expiring qualifications, and a fully worked relief-chain
scenario (see below) so every feature has something real to
demonstrate.

## Feature Summary

| Feature | Where |
|---|---|
| Workforce KPI dashboard | `/` |
| Employee roster with search | `/employees` |
| Employee detail: role, assignments, qualifications, history | `/employees/[id]` |
| "Who can replace this employee?" eligibility search | Employee detail page |
| Assignment-extension scenario simulation | Employee detail page, `/simulate` |
| Sites & staffing coverage | `/sites` |
| Relief-due, qualification-risk, and staffing-shortage views | Dashboard |
| AI Operations Assistant - ask workforce questions in plain language | `/assistant` |

## Screenshots

| Dashboard | Scenario Simulation |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Scenario simulation result](docs/screenshots/scenario-simulation.png) |

| Employee Detail | Sites & Staffing Coverage |
|---|---|
| ![Employee detail](docs/screenshots/employee-detail.png) | ![Sites](docs/screenshots/sites.png) |

## Architecture Overview

```
Next.js (TypeScript) frontend
        |  REST / JSON
        v
FastAPI routes  ->  Domain / business-rule layer  ->  SQLAlchemy models
                                                              |
                                                              v
                                                         PostgreSQL
```

Full detail, including a diagram of how the (future) AI assistant
attaches to this same stack, is in [docs/architecture.md](docs/architecture.md).

## Technology Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic (migrations)
- **AI:** Anthropic Messages API (tool/function calling) behind a small vendor-neutral provider interface
- **Database:** PostgreSQL
- **Testing:** pytest (backend business rules, AI tool layer, API), TypeScript compiler + ESLint (frontend)

## Data Model Overview

Roles, Sites, and Qualifications are reference data. Employees hold a
Role and zero or more EmployeeQualifications (each with issue/expiry
dates). Assignments deploy an Employee to a Site under a Role for a
date window, and can point at the assignment they relieve
(`relieving_assignment_id`), forming the relief chain the simulation
engine walks. WorkforceMovements are the discrete, dated events
(mobilize, rotate out, relieve, etc.) around those assignments.
SiteStaffingRequirements and RoleQualificationRequirements are the two
small "rules as data" tables the eligibility and staffing engines
read from. Full schema: [database/schema.sql](database/schema.sql).

## Deterministic Rules

Every eligibility, relief, staffing, and simulation rule is documented
- with the exact check names, what they test, and worked examples -
in [docs/business-rules.md](docs/business-rules.md). That document
also walks through the seeded John Smith scenario end-to-end.

## Sample Use Cases

- **"Who needs relief in the next 30 days?"** -> Dashboard's Upcoming Relief widget, or `GET /api/relief/due?window_days=30`.
- **"Who can replace John Smith?"** -> John Smith's employee detail page, or `GET /api/assignments/{id}/replacement-candidates`.
- **"What happens if John Smith stays 14 more days?"** -> Scenario Simulation on his employee detail page (or `/simulate`), or `POST /api/assignments/{id}/simulate-extension`. This reproduces the exact downstream conflict documented in [business-rules.md](docs/business-rules.md#seeded-demonstration-scenario): a delayed reliever, a missed commitment at a second site, a staffing shortage, and a correctly-filtered list of eligible alternatives.
- **Any of the above, asked in plain English** -> the AI Operations Assistant at `/assistant`, or `POST /api/assistant/chat`. It answers by calling the exact same deterministic capabilities listed above - see [docs/ai-architecture.md](docs/ai-architecture.md).

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# create the database (see database/README.md for the exact commands)
cp .env.example .env   # DATABASE_URL is required - no default is built in
alembic upgrade head
python -m app.seed.generate_synthetic_data

uvicorn app.main:app --reload
# API now at http://localhost:8000, interactive docs at /docs
```

The AI Operations Assistant (`/assistant`, `POST /api/assistant/chat`) is optional: leave
`LLM_API_KEY` blank in `.env` and every other Kinvera feature works normally - the assistant
endpoint reports itself as unconfigured (503) instead of the app failing to start. To enable it,
set `LLM_API_KEY` to a real [Anthropic API key](https://console.anthropic.com/) in your own
untracked `.env` - never commit one.

### Frontend

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL, defaults to localhost:8000
npm install
npm run dev
# App now at http://localhost:3000
```

## Testing

```bash
# Backend business rules + API integration tests (from the kinvera/ root)
pytest

# Frontend type checking and linting
cd frontend
npx tsc --noEmit
npx eslint .
```

The pytest suite covers, at minimum: every eligibility rule in
isolation (valid replacement, wrong role, inactive/unavailable
employee, expired qualification, qualification expiring mid-assignment,
overlapping assignment, future-commitment conflict, rest-rotation
violation), relief-due window boundaries, the extension-simulation
engine (non-mutation, date math, conflict detection, staffing-shortage
detection, and the full seeded John Smith +14-day scenario), and the
entire AI layer (tool-by-tool correctness, ambiguity handling,
grounding, hallucination resistance, and the read-only guarantee) -
all driven by a scripted fake LLM provider, with no live API call
required to run the suite.

## AI Operations Assistant (Phase 2)

**Implemented.** An operations manager can ask questions like *"Can Ahmed replace John Smith?"*
or *"What happens if John Smith stays another 14 days?"* at `/assistant` in plain language. The
LLM identifies which trusted Kinvera capability answers the question, calls it, and explains the
structured result it gets back - it never evaluates eligibility, staffing, or simulation outcomes
itself, and it cannot write to the database (no tool in its registry is a write operation). Full
architecture, request-flow diagram, and the hallucination-resistance mechanism:
[docs/ai-architecture.md](docs/ai-architecture.md).

## Deployment

The application is deployment-ready for Vercel (frontend), Render
(backend), and Neon (PostgreSQL) - configuration only reads from
environment variables, with no hard-coded local database credentials
or CORS origins. It has not been deployed. See
[docs/deployment.md](docs/deployment.md) for the exact settings to
enter in each platform's dashboard.

## Current Limitations

See [docs/business-rules.md#limitations](docs/business-rules.md#limitations)
for the specific rule approximations (exact-only role matching,
availability as a snapshot rather than a leave calendar, a
one-hop-deep simulation chain, single-number staffing minimums), and
[docs/ai-architecture.md#ai-limitations](docs/ai-architecture.md#ai-limitations-stated-plainly-per-the-projects-own-principle)
for the AI assistant's own stated limits (in-memory-only conversation history, and no live-model
testing was possible in the environment this was built in - only against a scripted fake
provider). Beyond that: there is no authentication and no CI/CD pipeline. The application is
configured to be deployable (see [Deployment](#deployment) above) but has not actually been
deployed anywhere.

## Roadmap

- Persist AI conversation history in PostgreSQL instead of in-memory.
- Leave/absence calendar to replace the availability-status snapshot.
- Multi-hop relief-chain simulation.
- Role-substitution rules (which roles can cover which gaps).
- Authentication and role-based access for operations managers vs. read-only viewers.
- Actual deployment (Vercel + Render + Neon are configured but not yet live), plus CI and containerization.

## Repository Structure

```
kinvera/
├── frontend/        Next.js + TypeScript dashboard
├── backend/         FastAPI app: models, domain rules, API routes, seed data
├── database/        Schema reference and local setup notes
├── tests/backend/   pytest suite (business rules + API integration)
├── docs/            architecture.md, business-rules.md, screenshots/
├── README.md
├── .gitignore
└── LICENSE
```
