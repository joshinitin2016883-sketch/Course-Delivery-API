"""Adding, editing, reordering and removing a course's lessons. Every change is logged against the course.

Positions always run 1, 2, 3, ... with no gaps, and each function keeps it that way.
Each function locks the course row first (course_service.lock_course), like every other change to a course.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Action, Lesson, User
from app.schemas.lessons import LessonIn
from app.services import activity_log
from app.services.course_service import lock_course
from app.services.errors import Conflict, NotFound
from app.services.permissions import require_instructor


def add_lesson(db: Session, actor: User, course_id: int, data: LessonIn) -> Lesson:
    """Add a lesson at the end of the course's running order."""
    require_instructor(actor)
    course = lock_course(db, course_id)
    position = len(_lessons_in_order(db, course.id)) + 1
    lesson = Lesson(course_id=course.id, title=data.title, content=data.content, position=position)
    db.add(lesson)
    db.flush()  # sends the INSERT now, so lesson.id exists for the log row
    details = {"lesson_id": lesson.id, "title": lesson.title, "position": position}
    activity_log.record(db, course.id, actor, Action.LESSON_ADDED, details)
    db.commit()
    return lesson


def edit_lesson(db: Session, actor: User, course_id: int, lesson_id: int, data: LessonIn) -> Lesson:
    """Edit a lesson's title and content. Its position only changes through reorder_lessons."""
    require_instructor(actor)
    course = lock_course(db, course_id)
    lesson = _get_lesson(db, course.id, lesson_id)
    changes = activity_log.apply_changes(lesson, data.model_dump())
    if changes:  # saving the same values again is not a change, so it isn't logged
        details = {"lesson_id": lesson.id, "title": lesson.title, "changes": changes}
        activity_log.record(db, course.id, actor, Action.LESSON_EDITED, details)
        db.commit()
    return lesson


def remove_lesson(db: Session, actor: User, course_id: int, lesson_id: int) -> None:
    """Delete a lesson and close the gap it leaves. The log keeps its title and old position."""
    require_instructor(actor)
    course = lock_course(db, course_id)
    lesson = _get_lesson(db, course.id, lesson_id)
    details = {"lesson_id": lesson.id, "title": lesson.title, "position": lesson.position}
    activity_log.record(db, course.id, actor, Action.LESSON_REMOVED, details)
    remaining = [other for other in _lessons_in_order(db, course.id) if other.id != lesson.id]
    db.delete(lesson)
    _renumber(remaining)
    db.commit()


def reorder_lessons(db: Session, actor: User, course_id: int, lesson_ids: list[int]) -> list[Lesson]:
    """Put the course's lessons in the given order. The list must name every lesson exactly once."""
    require_instructor(actor)
    course = lock_course(db, course_id)
    lessons = _lessons_in_order(db, course.id)
    current_ids = [lesson.id for lesson in lessons]
    # Comparing sorted lists catches a missing lesson, a lesson from elsewhere, and a repeated id.
    if sorted(lesson_ids) != sorted(current_ids):
        raise Conflict(
            "The new order must list every lesson of this course exactly once. "
            "The course may have changed since you loaded it: reload it and try again."
        )
    if lesson_ids == current_ids:
        return lessons  # same order as before: not a change, so nothing is logged
    lessons_by_id = {lesson.id: lesson for lesson in lessons}
    new_order = [lessons_by_id[lesson_id] for lesson_id in lesson_ids]
    _renumber(new_order)
    activity_log.record(db, course.id, actor, Action.LESSONS_REORDERED, {"from": current_ids, "to": lesson_ids})
    db.commit()
    return new_order


def _get_lesson(db: Session, course_id: int, lesson_id: int) -> Lesson:
    """The lesson, but only if it belongs to the course named in the URL."""
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course_id:
        raise NotFound("Lesson not found in this course.")
    return lesson


def _lessons_in_order(db: Session, course_id: int) -> list[Lesson]:
    return list(db.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.position)))


def _renumber(lessons: list[Lesson]) -> None:
    """Give the lessons positions 1, 2, 3, ... in list order."""
    for position, lesson in enumerate(lessons, start=1):
        lesson.position = position
