"""The lesson_completions table: one row for each lesson a learner has marked complete."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LessonCompletion(Base):
    __tablename__ = "lesson_completions"
    __table_args__ = (
        # A lesson counts once per enrolment, however many times "Mark complete" is pressed.
        UniqueConstraint("enrollment_id", "lesson_id", name="uq_lesson_completions_enrollment_id_lesson_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"))
    # RESTRICT: the database refuses to delete a lesson that any learner has completed.
    # Indexed (migration 0005) so that check, and "has anyone completed this lesson?", don't scan the table.
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="RESTRICT"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
