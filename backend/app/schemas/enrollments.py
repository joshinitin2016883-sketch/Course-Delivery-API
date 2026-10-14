"""Response bodies for enrolments and a learner's progress."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CourseSummaryOut(BaseModel):
    """Just enough about a course to list it. The status shows when a course has been archived."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    status: str


class EnrollmentOut(BaseModel):
    """One learner's enrolment in one course, with their progress through it."""

    course: CourseSummaryOut
    status: str
    lessons_done: int
    lessons_total: int
    enrolled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_activity_at: datetime | None


class LearnerOut(BaseModel):
    id: int
    full_name: str
    email: str


class LearnerProgressOut(BaseModel):
    """One enrolled learner's progress, as instructors see it on a course's progress list."""

    learner: LearnerOut
    status: str
    lessons_done: int
    lessons_total: int
    enrolled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_activity_at: datetime | None


class ProgressOut(BaseModel):
    """A learner's own progress through one course, including which lessons they have completed."""

    status: str
    lessons_done: int
    lessons_total: int
    completed_lesson_ids: list[int]
    enrolled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_activity_at: datetime | None
