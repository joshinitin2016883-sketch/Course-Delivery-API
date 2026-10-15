"""The instructors' dashboard (goal 8): headline numbers, enrolments by course and state, and course completions
over the last eight weeks. The database does all the counting, with aggregates.

The clock is the database's now(), in every query here, so the numbers agree with each other. Months and weeks
are calendar ones in UTC, and a week starts on Monday (Postgres's date_trunc('week')).
"""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Course, CourseStatus, Enrollment, EnrollmentStatus, Role, User
from app.schemas.dashboard import CourseStateCounts, DashboardOut, WeekCompletions
from app.services.permissions import require_instructor

WEEKS = 8


def dashboard(db: Session, viewer: User) -> DashboardOut:
    require_instructor(viewer)
    this_month = func.date_trunc("month", func.now(), "UTC")
    return DashboardOut(
        learners=db.scalar(select(func.count()).select_from(User).where(User.role == Role.LEARNER)),
        published_courses=db.scalar(
            select(func.count()).select_from(Course).where(Course.status == CourseStatus.PUBLISHED)
        ),
        # A completion is a learner finishing a whole course. None can be in the future, so only the start matters.
        completions_this_month=db.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.completed_at >= this_month)
        ),
        # Each learner once, however many courses they're in the middle of. Progress in an archived course is
        # frozen (Decision 17), so it isn't "currently" in progress.
        learners_in_progress=db.scalar(
            select(func.count(func.distinct(Enrollment.user_id)))
            .join(Course, Course.id == Enrollment.course_id)
            .where(Enrollment.status == EnrollmentStatus.IN_PROGRESS, Course.status != CourseStatus.ARCHIVED)
        ),
        by_course=_by_course(db),
        completions_by_week=_by_week(db),
    )


def _by_course(db: Session) -> list[CourseStateCounts]:
    """Every course with at least one enrolment, sorted like the course list's titles (Decision 26)."""
    rows = db.execute(
        select(
            Course.id,
            Course.title,
            Course.status,
            func.count().filter(Enrollment.status == EnrollmentStatus.NOT_STARTED),
            func.count().filter(Enrollment.status == EnrollmentStatus.IN_PROGRESS),
            func.count().filter(Enrollment.status == EnrollmentStatus.COMPLETED),
        )
        .join(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id)
        .order_by(func.lower(Course.title).collate("C"), Course.id)
    ).all()
    return [
        CourseStateCounts(
            id=course_id, title=title, status=status, not_started=not_started, in_progress=in_progress, completed=done
        )
        for course_id, title, status, not_started, in_progress, done in rows
    ]


# The last WEEKS Mondays (UTC), oldest first, from generate_series so a week with no completions still gets a
# row with 0. Each completion is counted in the week its completed_at falls in.
# Date arithmetic on a timestamptz normally happens in the session's time zone, where a daylight-saving change
# would shift the weeks off midnight UTC by an hour. So both the subtraction (date_subtract) and the weekly step
# (generate_series's last argument) are done in UTC. Both need Postgres 16 or later.
WEEKS_SQL = text("""
    SELECT (weeks.starts AT TIME ZONE 'UTC')::date AS week_start,
           count(enrollments.id) AS completions,
           weeks.starts = date_trunc('week', now(), 'UTC') AS partial
    FROM generate_series(
             date_subtract(date_trunc('week', now(), 'UTC'), make_interval(weeks => :weeks_back), 'UTC'),
             date_trunc('week', now(), 'UTC'),
             interval '1 week',
             'UTC'
         ) AS weeks(starts)
    LEFT JOIN enrollments ON date_trunc('week', enrollments.completed_at, 'UTC') = weeks.starts
    GROUP BY weeks.starts
    ORDER BY weeks.starts
""")


def _by_week(db: Session) -> list[WeekCompletions]:
    rows = db.execute(WEEKS_SQL, {"weeks_back": WEEKS - 1}).all()
    return [WeekCompletions(week_start=start, completions=count, partial=partial) for start, count, partial in rows]
