"""Inactivity alerts (goal 10): learners who started a course and then went quiet.

A learner has an alert on a course when their enrolment is in progress, the course is published, and their
last completed lesson was more than 14 days ago, unless an instructor has dismissed the alert for this quiet
spell. Alerts are worked out whenever they are read, from the database's now(), so no background job is needed.
Every instructor sees every alert, and a dismissal hides it for all of them (Decision 3).
"""
from datetime import timedelta

from sqlalchemy import and_, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import AlertDismissal, Course, CourseStatus, Enrollment, EnrollmentStatus, User
from app.schemas.alerts import AlertCourseOut, AlertOut
from app.schemas.enrollments import LearnerOut
from app.services.errors import Conflict
from app.services.permissions import require_instructor

QUIET_FOR = timedelta(days=14)

# How long since the learner last completed a lesson. Subtracting one timestamp from another gives the exact
# time between them, whatever the session's time zone, so a daylight-saving change can't shift an alert.
TIME_QUIET = func.now() - Enrollment.last_activity_at

# The alert rule, apart from dismissals. Queries using it join enrollments to courses.
QUIET_TOO_LONG = and_(
    Enrollment.status == EnrollmentStatus.IN_PROGRESS,
    Course.status == CourseStatus.PUBLISHED,  # progress in an archived course is frozen (Decision 17)
    TIME_QUIET > QUIET_FOR,  # more than 14 days: exactly 14 isn't an alert yet
)

# Dismissed for this quiet spell. When the learner completes another lesson, last_activity_at moves on and the
# old dismissal stops matching, so the alert comes back if they then go quiet for another 14 days.
DISMISSED = exists().where(
    AlertDismissal.enrollment_id == Enrollment.id,
    AlertDismissal.quiet_since == Enrollment.last_activity_at,
)


def list_alerts(db: Session, viewer: User) -> list[AlertOut]:
    """Every current alert, the learner who has been quiet the longest first."""
    require_instructor(viewer)
    rows = db.execute(
        select(Enrollment, User, Course, TIME_QUIET)
        .join(Course, Course.id == Enrollment.course_id)
        .join(User, User.id == Enrollment.user_id)
        .where(QUIET_TOO_LONG, ~DISMISSED)
        .order_by(Enrollment.last_activity_at, Enrollment.id)
    ).all()
    return [
        AlertOut(
            learner=LearnerOut(id=learner.id, full_name=learner.full_name, email=learner.email),
            course=AlertCourseOut(id=course.id, title=course.title),
            last_activity_at=enrollment.last_activity_at,
            days_quiet=time_quiet.days,
        )
        for enrollment, learner, course, time_quiet in rows
    ]


def dismiss_alert(db: Session, viewer: User, course_id: int, learner_id: int) -> None:
    """Dismiss a learner's alert on a course, for every instructor, until the learner is active again.

    A 409 when there's nothing to dismiss: the learner has completed a lesson since, the course was archived,
    or the alert was already dismissed. The unique (enrollment_id, quiet_since) is the "already dismissed"
    check, as the unique enrolment is the "already enrolled" one (Decision 18): of two instructors dismissing
    at the same moment, one records the dismissal and the other gets a 409, never a 500.
    Not written to the activity log, like enrolments (Decision 22): dismissed_by and dismissed_at record it."""
    require_instructor(viewer)
    enrollment = db.scalar(
        select(Enrollment)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.course_id == course_id, Enrollment.user_id == learner_id, QUIET_TOO_LONG)
    )
    if enrollment is None:
        raise Conflict("This learner has no alert on this course any more.")
    # RETURNING gives the new row's id, or nothing when the constraint skipped it.
    dismissal_id = db.scalar(
        insert(AlertDismissal)
        .values(enrollment_id=enrollment.id, quiet_since=enrollment.last_activity_at, dismissed_by=viewer.id)
        .on_conflict_do_nothing(constraint="uq_alert_dismissals_enrollment_id_quiet_since")
        .returning(AlertDismissal.id)
    )
    if dismissal_id is None:
        raise Conflict("This alert has already been dismissed.")
    db.commit()
