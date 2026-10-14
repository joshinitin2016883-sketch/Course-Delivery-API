"""Request and response bodies for courses."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import Category, CourseStatus
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


class CourseListQuery(BaseModel):
    """The query parameters of GET /courses. A value outside these rules is a 422 before any query runs."""

    q: str | None = Field(default=None, max_length=100)  # searched in titles and descriptions
    category: Category | None = None
    status: CourseStatus | None = None
    instructor_id: int | None = None
    sort: Literal["title", "created_at", "enrollment_count"] = "created_at"
    order: Literal["asc", "desc"] | None = None  # when left out, each sort has its own default
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CourseListItem(BaseModel):
    """One row of the course list."""

    id: int
    title: str
    description: str
    category: str
    status: str
    created_at: datetime
    instructor: InstructorOut
    enrollment_count: int
    enrolled: bool  # whether the viewer is enrolled; always false for instructors


class CoursePage(BaseModel):
    items: list[CourseListItem]
    total: int  # every course that matches, not just this page
    page: int
    page_size: int
