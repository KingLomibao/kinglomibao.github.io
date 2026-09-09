# Database

Kinvera uses PostgreSQL. The schema's source of truth is the
SQLAlchemy models in `backend/app/models/`, versioned through Alembic
migrations in `backend/alembic/versions/`. `schema.sql` in this folder
is a hand-maintained reference copy of that schema for readers who
want to see the tables without a Python environment - if it ever
drifts from the real migrations, the migrations win.

## Local setup

```bash
# Create the role and databases (once)
sudo -u postgres psql -c "CREATE USER kinvera WITH PASSWORD 'kinvera' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE kinvera OWNER kinvera;"
sudo -u postgres psql -c "CREATE DATABASE kinvera_test OWNER kinvera;"

# Apply migrations
cd backend
alembic upgrade head

# Load the synthetic dataset (safe to re-run; it wipes and rebuilds)
python -m app.seed.generate_synthetic_data
```

`kinvera_test` is used by the pytest suite (see `tests/backend/conftest.py`) and is never touched by the seed script.

## Why Alembic

A migration is a small, versioned script that describes one change to
the database schema (add a table, add a column, etc.). Instead of
hand-running `CREATE TABLE` statements against every environment,
Alembic generates that SQL from the SQLAlchemy models and tracks,
inside the database itself (the `alembic_version` table), which
migrations have already been applied. That means:

- The schema's history lives in git, next to the code that depends on it.
- Any environment can be brought up to the exact same schema with one command (`alembic upgrade head`).
- Future schema changes (e.g. Phase 2 adding an AI conversation log) are additive migrations, not manual edits to a live database.

See `docs/architecture.md` for how the tables relate to each other.
