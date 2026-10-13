"""The activity_log table: an append-only history of every change to a course, and the comments left on it.

Rows are only ever inserted. No code updates or deletes them, and a database trigger
(migration 0002) rejects any UPDATE, DELETE or TRUNCATE, whoever sends it.
"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User


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
    COMMENTED = "commented"


class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'edited', 'lesson_added', 'lesson_edited', 'lessons_reordered', "
            "'lesson_removed', 'published', 'archived', 'restored', 'commented')",
            name="action_allowed",
        ),
        # Matches the feed's query: one course's entries, newest first by id (migration 0003).
        Index("ix_activity_log_course_id_id", "course_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    # Who made the change.
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # One of Action. The database checks it too (migration 0003): this table is append-only,
    # so a row with a wrong action could never be corrected afterwards.
    action: Mapped[str] = mapped_column(String(30))
    # What changed, e.g. {"title": {"from": "Old", "to": "New"}}. Lessons are named here rather than
    # linked by a foreign key, so the history still reads correctly after a lesson is removed.
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped[User] = relationship()
