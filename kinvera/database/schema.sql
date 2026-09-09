-- Kinvera database schema (reference copy)
--
-- This file is documentation, not the source of truth: the actual
-- schema is defined by the SQLAlchemy models in
-- backend/app/models/*.py and versioned by the Alembic migrations in
-- backend/alembic/versions/. Run `alembic upgrade head` from
-- backend/ to create or update a real database. This file is kept in
-- sync by hand so the schema can be read without a Python environment.
--
-- See docs/architecture.md for how these tables relate to each other,
-- and docs/business-rules.md for what each status/date field means to
-- the business-rule engine.

-- ---------------------------------------------------------------
-- Enumerated types
-- ---------------------------------------------------------------

CREATE TYPE role_category AS ENUM ('technical', 'supervisory');
CREATE TYPE site_status AS ENUM ('active', 'demobilizing', 'inactive');
CREATE TYPE employment_status AS ENUM ('active', 'inactive', 'terminated');
CREATE TYPE availability_status AS ENUM ('available', 'assigned', 'on_leave', 'unavailable');
CREATE TYPE assignment_status AS ENUM ('planned', 'active', 'completed', 'cancelled');
CREATE TYPE movement_type AS ENUM ('mobilization', 'demobilization', 'rotation_out', 'rotation_in', 'relief_in', 'relief_out');

-- ---------------------------------------------------------------
-- Reference data: roles, sites, qualifications
-- ---------------------------------------------------------------

CREATE TABLE roles (
    id       SERIAL PRIMARY KEY,
    code     VARCHAR(40) NOT NULL UNIQUE,
    name     VARCHAR(100) NOT NULL,
    category role_category NOT NULL
);

CREATE TABLE sites (
    id       SERIAL PRIMARY KEY,
    code     VARCHAR(20) NOT NULL UNIQUE,
    name     VARCHAR(150) NOT NULL,
    location VARCHAR(150) NOT NULL,
    status   site_status NOT NULL
);

CREATE TABLE qualifications (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(40) NOT NULL UNIQUE,
    name        VARCHAR(150) NOT NULL,
    description VARCHAR(300)
);

-- Which qualifications a role requires. The eligibility engine reads
-- this table to know which EmployeeQualification rows to check - the
-- requirement is data, never hard-coded in application code.
CREATE TABLE role_qualification_requirements (
    id               SERIAL PRIMARY KEY,
    role_id          INTEGER NOT NULL REFERENCES roles(id),
    qualification_id INTEGER NOT NULL REFERENCES qualifications(id),
    mandatory        BOOLEAN NOT NULL DEFAULT true
);

-- Minimum headcount of a role required at a site. Compared against
-- currently-active assignments to detect staffing shortages.
CREATE TABLE site_staffing_requirements (
    id                SERIAL PRIMARY KEY,
    site_id           INTEGER NOT NULL REFERENCES sites(id),
    role_id           INTEGER NOT NULL REFERENCES roles(id),
    minimum_required  INTEGER NOT NULL
);

-- ---------------------------------------------------------------
-- Workforce
-- ---------------------------------------------------------------

CREATE TABLE employees (
    id                   SERIAL PRIMARY KEY,
    employee_number      VARCHAR(20) NOT NULL UNIQUE,
    first_name           VARCHAR(80) NOT NULL,
    last_name            VARCHAR(80) NOT NULL,
    role_id              INTEGER NOT NULL REFERENCES roles(id),
    employment_status    employment_status NOT NULL,
    -- Why this employee is/isn't available when not currently
    -- assigned (resting, on leave, unavailable). Whether they ARE
    -- currently assigned is derived from `assignments`, not stored
    -- here, so the two can never silently disagree.
    availability_status  availability_status NOT NULL,
    home_location        VARCHAR(150),
    hire_date            DATE NOT NULL,
    active               BOOLEAN NOT NULL DEFAULT true
);

-- A qualification held by a specific employee, with the dates that
-- determine whether it's currently valid. Status ("valid" /
-- "expiring_soon" / "expired") is always computed from these two
-- dates, never stored as its own column.
CREATE TABLE employee_qualifications (
    id                SERIAL PRIMARY KEY,
    employee_id       INTEGER NOT NULL REFERENCES employees(id),
    qualification_id  INTEGER NOT NULL REFERENCES qualifications(id),
    issue_date        DATE NOT NULL,
    expiry_date       DATE NOT NULL
);

-- An employee deployed to a site, under a role, for a date window.
-- `relieving_assignment_id` links a reliever's assignment back to the
-- assignment it is scheduled to relieve - this is what lets the
-- system answer "who is planned to relieve whom" and walk the relief
-- chain in the extension-simulation engine.
CREATE TABLE assignments (
    id                        SERIAL PRIMARY KEY,
    employee_id               INTEGER NOT NULL REFERENCES employees(id),
    site_id                   INTEGER NOT NULL REFERENCES sites(id),
    role_id                   INTEGER NOT NULL REFERENCES roles(id),
    start_date                DATE NOT NULL,
    planned_end_date          DATE NOT NULL,
    actual_end_date           DATE,
    status                    assignment_status NOT NULL,
    relieving_assignment_id   INTEGER REFERENCES assignments(id),
    notes                     VARCHAR(300)
);

-- A discrete, dated workforce event (mobilizing, rotating out, being
-- relieved, etc.). Assignments describe periods; movements describe
-- the events around them, giving the "Upcoming Movements" view a
-- clean, chronological feed.
CREATE TABLE workforce_movements (
    id              SERIAL PRIMARY KEY,
    employee_id     INTEGER NOT NULL REFERENCES employees(id),
    assignment_id   INTEGER NOT NULL REFERENCES assignments(id),
    movement_type   movement_type NOT NULL,
    movement_date   DATE NOT NULL,
    from_site_id    INTEGER REFERENCES sites(id),
    to_site_id      INTEGER REFERENCES sites(id),
    notes           VARCHAR(300)
);
