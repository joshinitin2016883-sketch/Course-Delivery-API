"""The enrollments table: which learner is enrolled in which course, and how far they have got."""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.course import Course


class EnrollmentStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollments_course_id_user_id"),
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name="status_allowed"),
        # The status and the times can never disagree.
        CheckConstraint("(status = 'completed') = (completed_at IS NOT NULL)", name="completed_matches_completed_at"),
        CheckConstraint("(status = 'not_started') = (started_at IS NULL)", name="not_started_matches_started_at"),
        CheckConstraint("(started_at IS NULL) = (last_activity_at IS NULL)", name="started_matches_last_activity"),
        Index("ix_enrollments_user_id", "user_id"),
        Index("ix_enrollments_course_id_status", "course_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    # The learner. Only learners can be enrolled: the services check the role.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Every enrolment starts as not_started; completing lessons moves it on (enrollment_service).
    status: Mapped[str] = mapped_column(String(20), server_default=EnrollmentStatus.NOT_STARTED.value)
    # Who enrolled them: the learner themselves, or later an instructor (bulk enrolment).
    enrolled_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When the learner last completed a lesson. The inactivity alerts will read it.
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    course: Mapped[Course] = relationship()
