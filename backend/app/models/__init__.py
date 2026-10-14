"""All table models. Importing this package registers every table on Base.metadata, which Alembic reads."""
from app.models.activity_log import Action, ActivityLog
from app.models.base import Base
from app.models.course import Category, Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.lesson import Lesson
from app.models.lesson_completion import LessonCompletion
from app.models.user import Role, User

__all__ = [
    "Action",
    "ActivityLog",
    "Base",
    "Category",
    "Course",
    "CourseStatus",
    "Enrollment",
    "EnrollmentStatus",
    "Lesson",
    "LessonCompletion",
    "Role",
    "User",
]
