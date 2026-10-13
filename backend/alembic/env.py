"""Alembic's entry point: runs the migrations in alembic/versions against DATABASE_URL.

New migration:  python -m alembic revision --autogenerate -m "what changed"
Autogenerate compares the database with the models on Base.metadata and writes a draft;
always read and tidy the draft before applying it.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.core.config import DATABASE_URL
from app.models import Base

config = context.config

# Logging settings come from alembic.ini. Loggers that already exist (e.g. during tests) keep working.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """`python -m alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run the migrations in one transaction."""
    # NullPool: a single plain connection that is closed when the migration finishes.
    engine = create_engine(DATABASE_URL, poolclass=NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
