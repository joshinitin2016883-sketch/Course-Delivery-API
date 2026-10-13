"""Creating, viewing and editing courses, and moving them between draft, published and archived."""
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Action, Course, CourseStatus, Lesson, Role, User
from app.schemas.courses import CourseIn
from app.services import activity_log
from app.services.errors import Conflict, NotFound
from app.services.permissions import require_instructor


class Move(NamedTuple):
    from_status: CourseStatus
    to_status: CourseStatus
    action: Action  # what the log row records


# The only moves a course can make. Every other pair of status and move is refused.
MOVES = {
    "publish": Move(CourseStatus.DRAFT, CourseStatus.PUBLISHED, Action.PUBLISHED),
    "archive": Move(CourseStatus.PUBLISHED, CourseStatus.ARCHIVED, Action.ARCHIVED),
    "restore": Move(CourseStatus.ARCHIVED, CourseStatus.PUBLISHED, Action.RESTORED),
}


def create_course(db: Session, actor: User, data: CourseIn) -> Course:
    """Create a draft course. The instructor who creates it is recorded as its author."""
    require_instructor(actor)
    course = Course(title=data.title, description=data.description, category=data.category, instructor_id=actor.id)
    db.add(course)
    db.flush()  # sends the INSERT now, so course.id exists for the log row
    activity_log.record(db, course.id, actor, Action.CREATED, data.model_dump())
    db.commit()
    return course


def get_course(db: Session, viewer: User, course_id: int) -> Course:
    """A course the viewer may see. Instructors see every course; learners only published ones.
    For a learner, any other course is "not found", so they can't tell that a draft exists."""
    course = db.get(Course, course_id)
    if course is None:
        raise NotFound("Course not found.")
    if viewer.role != Role.INSTRUCTOR and course.status != CourseStatus.PUBLISHED:
        raise NotFound("Course not found.")
    return course


def lock_course(db: Session, course_id: int) -> Course:
    """Load the course and lock its row until this transaction ends (SELECT ... FOR UPDATE).

    Every change to a course or its lessons calls this before reading anything else, so two changes
    to the same course run one after the other. Without it, publishing a course and removing its last
    lesson could both succeed at the same moment.
    """
    course = db.get(Course, course_id, with_for_update=True)
    if course is None:
        raise NotFound("Course not found.")
    return course


def update_course(db: Session, actor: User, course_id: int, data: CourseIn) -> Course:
    """Edit the title, description and category. Any instructor may edit any course.
    The status can't be edited here: it only changes through change_status."""
    require_instructor(actor)
    course = lock_course(db, course_id)
    changes = activity_log.apply_changes(course, data.model_dump())
    if changes:  # saving the same values again is not a change, so it isn't logged
        activity_log.record(db, course.id, actor, Action.EDITED, changes)
        db.commit()
    return course


def change_status(db: Session, actor: User, course_id: int, move_name: str) -> Course:
    """Publish, archive or restore a course, if MOVES allows that move from the course's current status."""
    require_instructor(actor)  # before the lookup, so a learner gets 403 even for a course that doesn't exist
    move = MOVES[move_name]
    course = lock_course(db, course_id)
    if course.status != move.from_status:
        raise Conflict(
            f"Can't {move_name} this course: its status is {course.status}. "
            f"From {course.status}, the only allowed move is {_move_from(course.status)}."
        )
    if move.to_status == CourseStatus.PUBLISHED and _count_lessons(db, course.id) == 0:
        raise Conflict(
            f"Can't {move_name} this course: it has no lessons, and a published course needs at least one lesson."
        )
    course.status = move.to_status
    activity_log.record(db, course.id, actor, move.action, {"from": move.from_status, "to": move.to_status})
    db.commit()
    return course


def _move_from(status: str) -> str:
    """The name of the one move that starts from this status."""
    return next(name for name, move in MOVES.items() if move.from_status == status)


def _count_lessons(db: Session, course_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Lesson).where(Lesson.course_id == course_id))
