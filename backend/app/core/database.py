"""The database engine, and the factory that opens sessions on it."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

# pool_pre_ping checks a pooled connection still works before using it (Neon closes idle connections).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
