"""Creating, viewing and editing courses. (Publishing, archiving and restoring come in step 3.)"""
from sqlalchemy.orm import Session

from app.models import Action, Course, CourseStatus, Role, User
from app.schemas.courses import CourseIn
from app.services import activity_log
from app.services.errors import NotFound
from app.services.permissions import require_instructor


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


def update_course(db: Session, actor: User, course_id: int, data: CourseIn) -> Course:
    """Edit the title, description and category. Any instructor may edit any course."""
    require_instructor(actor)
    course = get_course(db, actor, course_id)
    changes = activity_log.apply_changes(course, data.model_dump())
    if changes:  # saving the same values again is not a change, so it isn't logged
        activity_log.record(db, course.id, actor, Action.EDITED, changes)
        db.commit()
    return course
