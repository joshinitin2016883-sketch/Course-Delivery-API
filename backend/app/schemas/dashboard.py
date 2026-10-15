"""Response body for the instructors' dashboard (goal 8)."""
from datetime import date

from pydantic import BaseModel


class CourseStateCounts(BaseModel):
    """One course's enrolments, split by progress state."""

    id: int
    title: str
    status: str
    not_started: int
    in_progress: int
    completed: int


class WeekCompletions(BaseModel):
    week_start: date  # a Monday, in UTC
    completions: int
    partial: bool  # true for the current week, which isn't over yet


class DashboardOut(BaseModel):
    learners: int  # every learner account
    published_courses: int
    completions_this_month: int  # courses completed in the current calendar month, in UTC
    learners_in_progress: int  # distinct learners in progress on a course that isn't archived
    by_course: list[CourseStateCounts]  # courses that have enrolments, by title
    completions_by_week: list[WeekCompletions]  # the last 8 weeks, oldest first, empty weeks included
