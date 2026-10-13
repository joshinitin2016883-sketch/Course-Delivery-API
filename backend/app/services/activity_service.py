"""Comments on a course, and reading a course's activity log.

Kept apart from activity_log.py: these functions need course_service (who can see which course),
and course_service itself uses activity_log, so putting them there would make the two import each other.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Action, ActivityLog, Role, User
from app.services import activity_log, course_service


def add_comment(db: Session, author: User, course_id: int, text: str) -> ActivityLog:
    """Add a comment to the course's log. Anyone who can see the course may comment, archived courses
    included: archived means the content is read-only, not the discussion. A comment is a log row,
    so the append-only trigger stops it ever being edited or deleted.

    A comment doesn't lock the course: it neither reads nor changes the course's state."""
    course = course_service.get_course(db, author, course_id)  # learners get 404 unless it is published
    entry = activity_log.record(db, course.id, author, Action.COMMENTED, {"text": text})
    db.commit()
    return entry


def list_activity(db: Session, viewer: User, course_id: int, limit: int, before: int | None) -> list[ActivityLog]:
    """One page of the course's log, newest first. Instructors see every entry; learners see only the
    comments, because the other entries hold old values from when the course was still a draft.

    To get the next, older page, pass the id of the last entry you received as `before`. Sorting and the
    cursor both use the id, so they always agree. A page shorter than `limit` means nothing older is left.
    """
    course = course_service.get_course(db, viewer, course_id)  # learners get 404 unless it is published
    query = select(ActivityLog).where(ActivityLog.course_id == course.id)
    if viewer.role != Role.INSTRUCTOR:
        query = query.where(ActivityLog.action == Action.COMMENTED)
    if before is not None:
        query = query.where(ActivityLog.id < before)
    # selectinload fetches the whole page's actors in one extra query, instead of one query per entry.
    query = query.order_by(ActivityLog.id.desc()).limit(limit).options(selectinload(ActivityLog.actor))
    return list(db.scalars(query))
