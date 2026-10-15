"""The alert_dismissals table: an instructor dismissed a learner's inactivity alert (goal 10).

A dismissal covers one quiet spell. quiet_since is the enrolment's last_activity_at when it was dismissed, so
once the learner completes another lesson the row no longer matches, and a new quiet spell can raise the alert
again. Rows are never deleted: they are the record of who dismissed what, and when.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertDismissal(Base):
    __tablename__ = "alert_dismissals"
    __table_args__ = (
        # One dismissal per quiet spell. This is the race-safe "already dismissed" check (alert_service).
        UniqueConstraint("enrollment_id", "quiet_since", name="uq_alert_dismissals_enrollment_id_quiet_since"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"))
    quiet_since: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # The instructor who dismissed it.
    dismissed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
