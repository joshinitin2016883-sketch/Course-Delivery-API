"""Request and response bodies for inactivity alerts (goal 10)."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.enrollments import LearnerOut


class AlertCourseOut(BaseModel):
    """Just enough of the course to name it and link to it."""

    id: int
    title: str


class AlertOut(BaseModel):
    """A learner who is in progress on a published course but hasn't completed a lesson for more than 14 days."""

    learner: LearnerOut
    course: AlertCourseOut
    last_activity_at: datetime
    days_quiet: int  # whole days since last_activity_at


class DismissAlertIn(BaseModel):
    """Which alert to dismiss: a learner on a course has at most one."""

    course_id: int
    learner_id: int
