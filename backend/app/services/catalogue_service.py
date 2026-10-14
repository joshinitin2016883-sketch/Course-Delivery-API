"""Finding courses (goal 6): one list of every course the viewer can see, with search, filters, sorting
and pages. All of it happens in the database: one query for the page, and one for the total."""
from sqlalchemy import ColumnElement, exists, false, func, or_, select
from sqlalchemy.orm import Session

from app.models import Course, CourseStatus, Enrollment, Role, User
from app.schemas.courses import CourseListItem, CourseListQuery, CoursePage, InstructorOut

# The direction a sort uses when the request doesn't give an order.
DEFAULT_ORDER = {"title": "asc", "created_at": "desc", "enrollment_count": "desc"}


def list_courses(db: Session, viewer: User, query: CourseListQuery) -> CoursePage:
    """One page of the courses the viewer can see that match the query, with the total number of matches."""
    conditions = _visible_to(viewer) + _filters(query)
    # Counted when read: every enrolment, whatever its state (there is no unenrolling).
    enrollment_count = (
        select(func.count(Enrollment.id))
        .where(Enrollment.course_id == Course.id)
        .scalar_subquery()
        .label("enrollment_count")
    )
    rows = db.execute(
        # Only the instructor's name is selected, never the whole user row (which holds the password hash).
        select(Course, User.full_name, enrollment_count, _enrolled(viewer).label("enrolled"))
        .join(User, User.id == Course.instructor_id)  # the instructor's name comes in the same query
        .where(*conditions)
        .order_by(*_order_by(query, enrollment_count))
        .limit(query.page_size)
        .offset((query.page - 1) * query.page_size)
    ).all()
    return CoursePage(
        items=[_to_item(course, name, count, enrolled) for course, name, count, enrolled in rows],
        total=_count_matches(db, conditions),
        page=query.page,
        page_size=query.page_size,
    )


def _visible_to(viewer: User) -> list[ColumnElement[bool]]:
    """Learners see published courses only. This is part of the query itself, so no parameter can widen it.
    Archived courses a learner is enrolled in aren't listed here: they're in My courses."""
    if viewer.role == Role.INSTRUCTOR:
        return []
    return [Course.status == CourseStatus.PUBLISHED]


def _filters(query: CourseListQuery) -> list[ColumnElement[bool]]:
    conditions = []
    search = (query.q or "").strip()  # spaces alone mean no search
    if search:
        pattern = f"%{_escape_like(search)}%"
        conditions.append(or_(Course.title.ilike(pattern, escape="\\"), Course.description.ilike(pattern, escape="\\")))
    if query.category is not None:
        conditions.append(Course.category == query.category)
    # For a learner this adds to "published only", so asking for drafts or archived courses matches nothing.
    if query.status is not None:
        conditions.append(Course.status == query.status)
    if query.instructor_id is not None:
        conditions.append(Course.instructor_id == query.instructor_id)
    return conditions


def _escape_like(text: str) -> str:
    """Make \\, % and _ in the user's text match themselves instead of acting as ILIKE wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _enrolled(viewer: User) -> ColumnElement[bool]:
    """Whether the viewer is enrolled in each course. Instructors can't enrol, so for them it's always false."""
    if viewer.role == Role.INSTRUCTOR:
        return false()
    return exists().where(Enrollment.course_id == Course.id, Enrollment.user_id == viewer.id)


def _order_by(query: CourseListQuery, enrollment_count: ColumnElement[int]) -> list[ColumnElement]:
    """The chosen sort, then the course id in the same direction as a tie-breaker, so pages never repeat
    or skip a course. Titles sort by lower(title) COLLATE "C": lower() removes case, and "C" compares byte
    by byte, so spaces and punctuation order the same way whatever the database's own collation is."""
    sort_column = {
        "title": func.lower(Course.title).collate("C"),
        "created_at": Course.created_at,
        "enrollment_count": enrollment_count,
    }[query.sort]
    if (query.order or DEFAULT_ORDER[query.sort]) == "asc":
        return [sort_column.asc(), Course.id.asc()]
    return [sort_column.desc(), Course.id.desc()]


def _count_matches(db: Session, conditions: list[ColumnElement[bool]]) -> int:
    """How many courses match, across all pages."""
    return db.scalar(select(func.count()).select_from(Course).where(*conditions))


def _to_item(course: Course, instructor_name: str, enrollment_count: int, enrolled: bool) -> CourseListItem:
    return CourseListItem(
        id=course.id,
        title=course.title,
        description=course.description,
        category=course.category,
        status=course.status,
        created_at=course.created_at,
        instructor=InstructorOut(id=course.instructor_id, full_name=instructor_name),
        enrollment_count=enrollment_count,
        enrolled=enrolled,
    )
