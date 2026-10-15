"""Enrolling learners in courses, completing lessons, and what each person sees of a course's progress.

A learner's progress through a course moves Not started -> In progress -> Completed. Nobody sets it
by hand: it moves as they complete lessons, through the one table of allowed moves below.
A learner only ever sees their own progress; instructors see everyone's.
"""
import re
from collections import Counter
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Course, CourseStatus, Enrollment, EnrollmentStatus, Lesson, LessonCompletion, Role, User
from app.schemas.courses import CourseOut
from app.schemas.enrollments import (
    BulkEnrollCounts,
    BulkEnrollOut,
    BulkEnrollRow,
    CourseSummaryOut,
    EnrollmentOut,
    LearnerOut,
    LearnerProgressOut,
    ProgressOut,
)
from app.services import course_service
from app.services.auth_service import normalize_email
from app.services.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from app.services.permissions import require_instructor, require_learner

# The only moves an enrolment can make. Any other move would be a bug in this file, so _move refuses it.
PROGRESS_MOVES = {
    EnrollmentStatus.NOT_STARTED: EnrollmentStatus.IN_PROGRESS,
    EnrollmentStatus.IN_PROGRESS: EnrollmentStatus.COMPLETED,
}


def enroll(db: Session, learner: User, course_id: int) -> EnrollmentOut:
    """Enrol the learner in a course. Learners see published courses, plus archived ones they are already
    enrolled in, so a new enrolment only ever lands on a published course: enrolling again in an archived
    course is "already enrolled", and any other course is "not found"."""
    require_learner(learner)  # before the lookup, so an instructor gets 403 even for a course that doesn't exist
    # A shared lock: an archive has to wait until this enrolment is saved, and the other way round.
    course = course_service.lock_course_for_share(db, course_id)
    if not course_service.can_see(db, learner, course):
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


# Bulk enrolment (goal 7). A pasted list may separate addresses with commas, semicolons, spaces or new lines.
MAX_BULK_ADDRESSES = 500
ADDRESS_SEPARATORS = re.compile(r"[,;\s]+")
# Deliberately simple, not a full RFC check: one "@", something before it, and a dot somewhere after it.
LOOKS_LIKE_EMAIL = re.compile(r"[^@]+@[^@]+\.[^@]+")


def bulk_enroll(db: Session, instructor: User, course_id: int, text: str) -> BulkEnrollOut:
    """Enrol every learner in a pasted list of email addresses, and report what happened to each address:
    enrolled, already enrolled, unknown (no account), invalid (not an address), or not a learner.

    All in one transaction. It takes the same shared lock on the course as a learner enrolling themselves,
    so an archive can't slip in meanwhile. New rows are inserted with ON CONFLICT DO NOTHING, so the unique
    constraint stays the "already enrolled" check (Decision 18): a learner who enrolled themselves a moment
    ago is skipped and reported as already enrolled, never a 500. Enrolments aren't logged (Decision 22);
    enrolled_by records which instructor enrolled each learner."""
    require_instructor(instructor)  # before the lookup, as everywhere else
    addresses, repeats_removed = _split_addresses(text)
    if not addresses:
        raise InvalidInput("Paste at least one email address.")
    if len(addresses) > MAX_BULK_ADDRESSES:
        raise InvalidInput(f"At most {MAX_BULK_ADDRESSES} addresses at a time; this list has {len(addresses)}.")
    course = course_service.lock_course_for_share(db, course_id)
    if course.status != CourseStatus.PUBLISHED:
        raise Conflict(f"Only a published course can take new learners, and this course is {course.status}.")

    valid = [address for address in addresses if LOOKS_LIKE_EMAIL.fullmatch(address)]
    accounts = {email: (user_id, role) for user_id, email, role in db.execute(
        select(User.id, User.email, User.role).where(User.email.in_(valid))
    )}
    learner_ids = [user_id for user_id, role in accounts.values() if role == Role.LEARNER]
    newly_enrolled = set()
    if learner_ids:
        rows = [{"course_id": course.id, "user_id": user_id, "enrolled_by": instructor.id} for user_id in learner_ids]
        # RETURNING lists only the rows really added; learners already enrolled are skipped by the constraint.
        newly_enrolled = set(db.scalars(
            insert(Enrollment)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_enrollments_course_id_user_id")
            .returning(Enrollment.user_id)
        ))
    db.commit()

    outcomes = [_bulk_outcome(address, accounts, newly_enrolled) for address in addresses]
    return BulkEnrollOut(
        results=[BulkEnrollRow(email=address, outcome=outcome) for address, outcome in zip(addresses, outcomes)],
        counts=BulkEnrollCounts(**Counter(outcomes)),
        repeats_removed=repeats_removed,
    )


def _split_addresses(text: str) -> tuple[list[str], int]:
    """The distinct addresses in the text, normalised like users.email (trimmed, lower-case), in the order
    they first appear; and how many repeats were dropped."""
    tokens = [normalize_email(token) for token in ADDRESS_SEPARATORS.split(text) if token]
    distinct = list(dict.fromkeys(tokens))  # a dict keeps the first of each key, in order
    return distinct, len(tokens) - len(distinct)


def _bulk_outcome(address: str, accounts: dict[str, tuple[int, str]], newly_enrolled: set[int]) -> str:
    if not LOOKS_LIKE_EMAIL.fullmatch(address):
        return "invalid"
    if address not in accounts:
        return "unknown"
    user_id, role = accounts[address]
    if role != Role.LEARNER:
        return "not_a_learner"
    return "enrolled" if user_id in newly_enrolled else "already_enrolled"


def complete_lesson(db: Session, learner: User, course_id: int, lesson_id: int) -> ProgressOut:
    """Mark a lesson complete. The first completion starts the course and completing the last remaining
    lesson finishes it; a one-lesson course does both at once. Completing a lesson twice changes nothing."""
    require_learner(learner)
    # Locks are always taken course first, then enrolment, like every other change, so two requests can't
    # deadlock. The course lock is shared: completions don't block each other, but an archive or a lesson
    # removal (which lock the course FOR UPDATE) waits for them, and they wait for it.
    course = course_service.lock_course_for_share(db, course_id)
    if not course_service.can_see(db, learner, course):
        raise NotFound("Course not found.")
    enrollment = db.scalar(
        select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == learner.id).with_for_update()
    )
    if enrollment is None:
        raise PermissionDenied("Enrol in this course first.")
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course.id:
        raise NotFound("Lesson not found in this course.")
    # Enrolled learners can still open an archived course and read it, but their progress there is frozen.
    if course.status == CourseStatus.ARCHIVED:
        raise Conflict("This course is archived, so you can't complete lessons in it any more.")

    if lesson.id not in _completed_lesson_ids(db, enrollment):
        # One timestamp for the completion row and the enrolment's times, so they always agree.
        now = datetime.now(timezone.utc)
        db.add(LessonCompletion(enrollment_id=enrollment.id, lesson_id=lesson.id, completed_at=now))
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


def view_course(db: Session, viewer: User, course_id: int) -> CourseOut:
    """A course page as the viewer may see it. Instructors see everything. A learner who isn't enrolled sees
    the title, description and lesson titles but not the lessons' content; an enrolled learner sees the
    content too, plus their own progress. Who may open the course at all is course_service.can_see."""
    course = course_service.get_course(db, viewer, course_id)
    page = CourseOut.model_validate(course)
    if viewer.role == Role.INSTRUCTOR:
        return page
    enrollment = course_service.find_enrollment(db, course.id, viewer.id)
    if enrollment is None:
        _hide_lesson_content(page)
    else:
        page.my_progress = _progress(db, enrollment)
    return page


def course_progress(db: Session, viewer: User, course_id: int) -> list[LearnerProgressOut]:
    """Every learner enrolled in the course with their progress, ordered by name. Instructors only."""
    require_instructor(viewer)  # before the lookup, so a learner gets 403 even for a course that doesn't exist
    course = course_service.get_course(db, viewer, course_id)
    lessons_total = _lessons_total(db, course.id)
    lessons_done = (
        select(func.count(LessonCompletion.id)).where(LessonCompletion.enrollment_id == Enrollment.id).scalar_subquery()
    )
    rows = db.execute(
        select(Enrollment, User, lessons_done)
        .join(User, User.id == Enrollment.user_id)
        .where(Enrollment.course_id == course.id)
        .order_by(User.full_name, User.id)
    ).all()
    return [
        LearnerProgressOut(
            learner=LearnerOut(id=learner.id, full_name=learner.full_name, email=learner.email),
            status=enrollment.status,
            lessons_done=done,
            lessons_total=lessons_total,
            enrolled_at=enrollment.enrolled_at,
            started_at=enrollment.started_at,
            completed_at=enrollment.completed_at,
            last_activity_at=enrollment.last_activity_at,
        )
        for enrollment, learner, done in rows
    ]


def _hide_lesson_content(page: CourseOut) -> None:
    """Before enrolling, a learner sees what the lessons are called but not what's in them."""
    for lesson in page.lessons:
        lesson.content = None


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
