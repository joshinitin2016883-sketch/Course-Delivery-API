"""Shared test setup.

Tests only ever touch the database in TEST_DATABASE_URL:
- DATABASE_URL is pointed at the test database *before* the app is imported;
- at the start of a run the test database is wiped and rebuilt by running the real Alembic migrations;
- each test runs inside a transaction that is rolled back afterwards, so tests can't affect each other.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

if not os.environ.get("TEST_DATABASE_URL"):
    raise RuntimeError("Set TEST_DATABASE_URL (see backend/.env.example) before running the tests.")
if os.environ["TEST_DATABASE_URL"] == os.environ.get("DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must be a different database from DATABASE_URL: the tests wipe it.")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

# Only now import the app, so that it connects to the test database.
import re
from contextlib import contextmanager

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Role, User

# bcrypt is slow on purpose, so users created without an explicit password share one precomputed hash.
DEFAULT_PASSWORD_HASH = hash_password("default-test-password")


@pytest.fixture(scope="session", autouse=True)
def fresh_test_database():
    """Once per test run: empty the test database, then build every table by running the migrations."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture
def db():
    """A session for one test. Services may call commit(); everything is still rolled back at the end."""
    connection = engine.connect()
    transaction = connection.begin()
    # With "create_savepoint", the session's commits only release savepoints inside our outer transaction.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """An HTTP client for the app. Its requests use the test's session instead of opening their own."""
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    """make_user(email=..., role=..., password=...) saves a user and returns it."""

    def _make_user(email="learner@example.com", role=Role.LEARNER, full_name="Test User", password=None):
        password_hash = hash_password(password) if password else DEFAULT_PASSWORD_HASH
        user = User(email=email, full_name=full_name, role=role, password_hash=password_hash)
        db.add(user)
        db.commit()
        return user

    return _make_user


@pytest.fixture
def auth_header():
    """auth_header(user) returns the Authorization header that user's browser would send."""

    def _auth_header(user):
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _auth_header


@pytest.fixture
def recorded_sql():
    """`with recorded_sql() as statements:` collects every SQL statement sent to the database in the block."""

    @contextmanager
    def _recorded_sql():
        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            yield statements
        finally:
            event.remove(engine, "before_cursor_execute", record)

    return _recorded_sql


@pytest.fixture
def first_index():
    """first_index(statements, pattern): position of the first statement matching the regular expression, or None."""

    def _first_index(statements, pattern):
        for index, statement in enumerate(statements):
            if re.search(pattern, statement, re.IGNORECASE | re.DOTALL):
                return index
        return None

    return _first_index
