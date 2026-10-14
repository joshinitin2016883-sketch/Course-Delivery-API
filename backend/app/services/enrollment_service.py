"""Enrolling learners in courses, completing lessons, and each learner's own list of courses.

A learner's progress through a course moves Not started -> In progress -> Completed. Nobody sets it
by hand: it moves as they complete lessons, through the one table of allowed moves below.
"""
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Course, Enrollment, EnrollmentStatus, Lesson, LessonCompletion, User
from app.schemas.enrollments import CourseSummaryOut, EnrollmentOut, ProgressOut
from app.services import course_service
from app.services.errors import Conflict, NotFound, PermissionDenied
from app.services.permissions import require_learner

# The only moves an enrolment can make. Any other move would be a bug in this file, so _move refuses it.
PROGRESS_MOVES = {
    EnrollmentStatus.NOT_STARTED: EnrollmentStatus.IN_PROGRESS,
    EnrollmentStatus.IN_PROGRESS: EnrollmentStatus.COMPLETED,
}


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


def complete_lesson(db: Session, learner: User, course_id: int, lesson_id: int) -> ProgressOut:
    """Mark a lesson complete. The first completion starts the course and completing the last remaining
    lesson finishes it; a one-lesson course does both at once. Completing a lesson twice changes nothing."""
    require_learner(learner)
    # Locks are always taken course first, then enrolment, like every other change, so two requests can't
    # deadlock. The course lock is shared: completions don't block each other, but an archive or a lesson
    # removal (which lock the course FOR UPDATE) waits for them, and they wait for it.
    course = course_service.lock_course_for_share(db, course_id)
    if not course_service.can_see(learner, course):
        raise NotFound("Course not found.")
    enrollment = db.scalar(
        select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == learner.id).with_for_update()
    )
    if enrollment is None:
        raise PermissionDenied("Enrol in this course first.")
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course.id:
        raise NotFound("Lesson not found in this course.")

    if lesson.id not in _completed_lesson_ids(db, enrollment):
        now = datetime.now(timezone.utc)
        db.add(LessonCompletion(enrollment_id=enrollment.id, lesson_id=lesson.id))
        if enrollment.status == EnrollmentStatus.NOT_STARTED:
            _move(enrollment, EnrollmentStatus.IN_PROGRESS, now)
        enrollment.last_activity_at = now
        # A Completed learner stays Completed, even after completing a lesson added later.
        if enrollment.status == EnrollmentStatus.IN_PROGRESS and _all_lessons_done(db, enrollment):
            _move(enrollment, EnrollmentStatus.COMPLETED, now)
        db.commit()
    return _progress(db, enrollment)


def complete_learners_with_nothing_left(db: Session, course: Course) -> None:
    """After a lesson is removed, move every In-progress learner who has now completed all the remaining
    lessons to Completed. completed_at is the removal time; last_activity_at stays as it was, because
    the learner didn't do anything. The caller holds the course lock, so no completion can run meanwhile."""
    now = datetime.now(timezone.utc)
    in_progress = db.scalars(
        select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.status == EnrollmentStatus.IN_PROGRESS)
    ).all()
    for enrollment in in_progress:
        if _all_lessons_done(db, enrollment):
            _move(enrollment, EnrollmentStatus.COMPLETED, now)


def list_my_courses(db: Session, learner: User) -> list[EnrollmentOut]:
    """Every course the learner is enrolled in, newest enrolment first, with their progress in each.
    Archived courses stay in the list; their status shows that they're archived."""
    require_learner(learner)
    return _enrollments_with_progress(db, Enrollment.user_id == learner.id)


def _move(enrollment: Enrollment, to_status: EnrollmentStatus, now: datetime) -> None:
    """Move the enrolment one step along PROGRESS_MOVES and record when it happened."""
    if PROGRESS_MOVES.get(enrollment.status) != to_status:
        raise RuntimeError(f"Illegal progress move: {enrollment.status} -> {to_status}")
    enrollment.status = to_status
    if to_status == EnrollmentStatus.IN_PROGRESS:
        enrollment.started_at = now
    else:
        enrollment.completed_at = now


def _completed_lesson_ids(db: Session, enrollment: Enrollment) -> list[int]:
    return list(
        db.scalars(
            select(LessonCompletion.lesson_id)
            .where(LessonCompletion.enrollment_id == enrollment.id)
            .order_by(LessonCompletion.lesson_id)
        )
    )


def _lessons_total(db: Session, course_id: int) -> int:
    return db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id == course_id))


def _all_lessons_done(db: Session, enrollment: Enrollment) -> bool:
    return len(_completed_lesson_ids(db, enrollment)) == _lessons_total(db, enrollment.course_id)


def _progress(db: Session, enrollment: Enrollment) -> ProgressOut:
    completed_lesson_ids = _completed_lesson_ids(db, enrollment)
    return ProgressOut(
        status=enrollment.status,
        lessons_done=len(completed_lesson_ids),
        lessons_total=_lessons_total(db, enrollment.course_id),
        completed_lesson_ids=completed_lesson_ids,
        enrolled_at=enrollment.enrolled_at,
        started_at=enrollment.started_at,
        completed_at=enrollment.completed_at,
        last_activity_at=enrollment.last_activity_at,
    )


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
