"""Enrolling learners in courses, and each learner's own list of courses with their progress."""
from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Enrollment, Lesson, LessonCompletion, User
from app.schemas.enrollments import CourseSummaryOut, EnrollmentOut
from app.services import course_service
from app.services.errors import Conflict, NotFound
from app.services.permissions import require_learner


def enroll(db: Session, learner: User, course_id: int) -> EnrollmentOut:
    """Enrol the learner in a course. Learners can only see published courses, so only a published
    course takes new enrolments; any other course is "not found"."""
    require_learner(learner)  # before the lookup, so an instructor gets 403 even for a course that doesn't exist
    # A shared lock: an archive has to wait until this enrolment is saved, and the other way round.
    course = course_service.lock_course_for_share(db, course_id)
    if not course_service.can_see(learner, course):
        raise NotFound("Course not found.")
    enrollment = Enrollment(course_id=course.id, user_id=learner.id, enrolled_by=learner.id)
    db.add(enrollment)
    try:
        # The unique constraint on (course_id, user_id) is the "already enrolled" check. Two requests at
        # the same moment can't both pass it: the database lets one row in and the other fails here.
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if isinstance(error.orig, UniqueViolation):
            raise Conflict("You are already enrolled in this course.") from error
        raise
    db.commit()
    return _enrollments_with_progress(db, Enrollment.id == enrollment.id)[0]


def list_my_courses(db: Session, learner: User) -> list[EnrollmentOut]:
    """Every course the learner is enrolled in, newest enrolment first, with their progress in each.
    Archived courses stay in the list; their status shows that they're archived."""
    require_learner(learner)
    return _enrollments_with_progress(db, Enrollment.user_id == learner.id)


def _enrollments_with_progress(db: Session, condition: ColumnElement[bool]) -> list[EnrollmentOut]:
    """The enrolments matching the condition, newest first, each with lessons done and lessons in total.
    Two queries in all, however many enrolments match."""
    lessons_done = (
        select(func.count(LessonCompletion.id)).where(LessonCompletion.enrollment_id == Enrollment.id).scalar_subquery()
    )
    lessons_total = select(func.count(Lesson.id)).where(Lesson.course_id == Enrollment.course_id).scalar_subquery()
    rows = db.execute(
        select(Enrollment, lessons_done, lessons_total)
        .where(condition)
        .order_by(Enrollment.enrolled_at.desc(), Enrollment.id.desc())
        .options(selectinload(Enrollment.course))  # all the courses in one extra query
    ).all()
    return [
        EnrollmentOut(
            course=CourseSummaryOut.model_validate(enrollment.course),
            status=enrollment.status,
            lessons_done=done,
            lessons_total=total,
            enrolled_at=enrollment.enrolled_at,
            started_at=enrollment.started_at,
            completed_at=enrollment.completed_at,
            last_activity_at=enrollment.last_activity_at,
        )
        for enrollment, done, total in rows
    ]
