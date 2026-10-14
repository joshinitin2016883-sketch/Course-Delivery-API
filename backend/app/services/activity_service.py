"""Comments on a course, and reading a course's activity log.

Kept apart from activity_log.py: these functions need course_service (who can see which course),
and course_service itself uses activity_log, so putting them there would make the two import each other.

Instructors can join any course's discussion. A learner must be enrolled: a course they can't see is
"not found" (404), and one they can see but aren't enrolled in is refused (403).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Action, ActivityLog, Course, Role, User
from app.services import activity_log, course_service
from app.services.errors import PermissionDenied


def add_comment(db: Session, author: User, course_id: int, text: str) -> ActivityLog:
    """Add a comment to the course's log. Archived courses take comments too: archived means the content
    is read-only, not the discussion. A comment is a log row, so the append-only trigger stops it ever
    being edited or deleted.

    A comment doesn't lock the course: it neither reads nor changes the course's state."""
    course = course_service.get_course(db, author, course_id)
    _ensure_can_join_discussion(db, author, course)
    entry = activity_log.record(db, course.id, author, Action.COMMENTED, {"text": text})
    db.commit()
    return entry


def list_activity(db: Session, viewer: User, course_id: int, limit: int, before: int | None) -> list[ActivityLog]:
    """One page of the course's log, newest first. Instructors see every entry; learners see only the
    comments, because the other entries hold old values from when the course was still a draft.

    To get the next, older page, pass the id of the last entry you received as `before`. Sorting and the
    cursor both use the id, so they always agree. A page shorter than `limit` means nothing older is left.
    """
    course = course_service.get_course(db, viewer, course_id)
    _ensure_can_join_discussion(db, viewer, course)
    query = select(ActivityLog).where(ActivityLog.course_id == course.id)
    if viewer.role != Role.INSTRUCTOR:
        query = query.where(ActivityLog.action == Action.COMMENTED)
    if before is not None:
        query = query.where(ActivityLog.id < before)
    # selectinload fetches the whole page's actors in one extra query, instead of one query per entry.
    query = query.order_by(ActivityLog.id.desc()).limit(limit).options(selectinload(ActivityLog.actor))
    return list(db.scalars(query))


def _ensure_can_join_discussion(db: Session, user: User, course: Course) -> None:
    """Instructors always can. A learner must be enrolled in the course."""
    if user.role != Role.INSTRUCTOR and course_service.find_enrollment(db, course.id, user.id) is None:
        raise PermissionDenied("Enrol in this course to join the discussion.")
