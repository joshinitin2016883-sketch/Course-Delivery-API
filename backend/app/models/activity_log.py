"""The activity_log table: an append-only history of every change to a course.

Rows are only ever inserted. No code updates or deletes them, and a database trigger
(migration 0002) rejects any UPDATE, DELETE or TRUNCATE, whoever sends it.
"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Action(StrEnum):
    CREATED = "created"
    EDITED = "edited"
    LESSON_ADDED = "lesson_added"
    LESSON_EDITED = "lesson_edited"
    LESSONS_REORDERED = "lessons_reordered"
    LESSON_REMOVED = "lesson_removed"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    RESTORED = "restored"


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    # Who made the change.
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # One of Action. Checked in code rather than by the database, because each step adds new actions.
    action: Mapped[str] = mapped_column(String(30))
    # What changed, e.g. {"title": {"from": "Old", "to": "New"}}. Lessons are named here rather than
    # linked by a foreign key, so the history still reads correctly after a lesson is removed.
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
