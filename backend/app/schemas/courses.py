"""Request and response bodies for courses."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models import Category
from app.schemas.enrollments import ProgressOut
from app.schemas.lessons import LessonOut

# Spaces around the text are removed before the length is checked, so "   " counts as empty.
CourseTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CourseDescription = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CourseIn(BaseModel):
    """Body for creating a course, and for editing one (all three fields are sent every time).
    There is no status field: every course starts as a draft, whatever the request says."""

    title: CourseTitle
    description: CourseDescription
    category: Category


class InstructorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class CourseOut(BaseModel):
    """A course with its lessons in running order."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    status: str
    instructor: InstructorOut
    created_at: datetime
    lessons: list[LessonOut]
    # Only for a learner enrolled in the course: their own progress. None for everyone else.
    my_progress: ProgressOut | None = None
