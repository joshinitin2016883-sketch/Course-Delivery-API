"""Request and response bodies for enrolments and a learner's progress."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints


class BulkEnrollIn(BaseModel):
    """A pasted or uploaded list of email addresses, as one block of text: the server splits it. Capped, so a
    huge paste is refused (422) before any work is done."""

    text: Annotated[str, StringConstraints(max_length=200_000)]


# What happened to one address in a bulk enrolment.
BulkOutcome = Literal["enrolled", "already_enrolled", "unknown", "invalid", "not_a_learner"]


class BulkEnrollRow(BaseModel):
    email: str
    outcome: BulkOutcome


class BulkEnrollCounts(BaseModel):
    """How many addresses had each outcome. An outcome that didn't happen counts 0."""

    enrolled: int = 0
    already_enrolled: int = 0
    unknown: int = 0
    invalid: int = 0
    not_a_learner: int = 0


class BulkEnrollOut(BaseModel):
    """One row per distinct address, in the order they were pasted, plus the totals."""

    results: list[BulkEnrollRow]
    counts: BulkEnrollCounts
    repeats_removed: int


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
