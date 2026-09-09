"""
Pytest fixtures shared by every backend test.

Each test runs inside its own database transaction that is always
rolled back afterwards (see the `db` fixture below). That means tests
can freely create employees, sites, and assignments without any
cleanup step, and without one test's data ever leaking into another.
"""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://kinvera:kinvera@localhost:5432/kinvera_test"
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, future=True)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
