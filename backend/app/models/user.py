"""The users table: everyone who can sign in, and their role."""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Role(StrEnum):
    INSTRUCTOR = "instructor"
    LEARNER = "learner"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('instructor', 'learner')", name="role_allowed"),
        # Emails are stored trimmed and lower-case, so the unique constraint treats "Sam@X.com" and "sam@x.com" as one.
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
