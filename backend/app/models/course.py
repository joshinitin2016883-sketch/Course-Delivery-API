"""The courses table."""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.lesson import Lesson
from app.models.user import User


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Category(StrEnum):
    ONBOARDING = "onboarding"
    COMPLIANCE = "compliance"
    SKILLS = "skills"


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="status_allowed"),
        CheckConstraint("category IN ('onboarding', 'compliance', 'skills')", name="category_allowed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    # Every course starts as a draft. Moving between states is step 3's job.
    status: Mapped[str] = mapped_column(String(20), server_default=CourseStatus.DRAFT.value)
    # The instructor who created the course. Any instructor may edit it; this records the author.
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    instructor: Mapped[User] = relationship()
    lessons: Mapped[list[Lesson]] = relationship(order_by=Lesson.position)
