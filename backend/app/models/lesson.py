"""The lessons table. Every lesson belongs to exactly one course and has a place in its running order."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        # No two lessons of a course share a position. The check is deferred to commit time,
        # so renumbering all of a course's lessons inside one transaction doesn't trip over itself.
        UniqueConstraint(
            "course_id", "position", name="uq_lessons_course_id_position", deferrable=True, initially="DEFERRED"
        ),
        CheckConstraint("position >= 1", name="position_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    # 1, 2, 3, ... with no gaps: services renumber after every removal or reorder.
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
