"""Goal 4 (course states) and goal 2 (archive and restore).

A course moves Draft -> Published -> Archived, and Archived -> Published when restored. Each move is checked
against one table (course_service.MOVES), and every other pair of status and move is refused.
Every change to a course locks the course row before reading or writing anything.
Archived courses are read-only, and a published course always keeps at least one lesson.
"""
import re
from contextlib import contextmanager

import pytest
from sqlalchemy import delete, event, select

from app.core.database import engine
from app.models import Action, ActivityLog, Course, CourseStatus, Lesson, Role

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}
# The one move allowed from each status, as the refusal messages name it.
ONLY_MOVE_FROM = {"draft": "publish", "published": "archive", "archived": "restore"}


@pytest.fixture
def instructor(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR)


@pytest.fixture
def headers(instructor, auth_header):
    return auth_header(instructor)


def create_course(client, headers, lesson_titles=()):
    """Create a draft course with the given lessons, through the API. Returns the course id and lesson ids."""
    course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]
    lessons_url = f"/courses/{course_id}/lessons"
    lesson_ids = [
        client.post(lessons_url, json={"title": title, "content": "Text"}, headers=headers).json()["id"]
        for title in lesson_titles
    ]
    return course_id, lesson_ids


def set_status(db, course_id, status):
    """Put a course straight into a status, so a test can start from any of them."""
    db.get(Course, course_id).status = status
    db.commit()


def status_in_database(db, course_id):
    db.expire_all()  # forget cached objects, so this really reads the database
    return db.get(Course, course_id).status


def log_entries(db, course_id):
    return list(db.scalars(select(ActivityLog).where(ActivityLog.course_id == course_id).order_by(ActivityLog.id)))


# --- The nine pairs of status and move -----------------------------------------------------------


@pytest.mark.parametrize(
    "start, move, end, action",
    [
        ("draft", "publish", "published", Action.PUBLISHED),
        ("published", "archive", "archived", Action.ARCHIVED),
        ("archived", "restore", "published", Action.RESTORED),
    ],
)
def test_the_three_allowed_moves_change_the_status_and_write_one_log_row(
    client, db, instructor, headers, start, move, end, action
):
    course_id, _ = create_course(client, headers, ["Alarms"])
    set_status(db, course_id, start)
    entries_before = len(log_entries(db, course_id))

    response = client.post(f"/courses/{course_id}/{move}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == end
    assert status_in_database(db, course_id) == end
    new_entries = log_entries(db, course_id)[entries_before:]
    assert [(entry.action, entry.actor_id, entry.details) for entry in new_entries] == [
        (action, instructor.id, {"from": start, "to": end})
    ]


@pytest.mark.parametrize(
    "start, move",
    [
        ("draft", "archive"),
        ("draft", "restore"),
        ("published", "publish"),
        ("published", "restore"),
        ("archived", "publish"),
        ("archived", "archive"),
    ],
)
def test_the_six_other_pairs_are_refused_and_change_nothing(client, db, headers, start, move):
    course_id, _ = create_course(client, headers, ["Alarms"])
    set_status(db, course_id, start)
    entries_before = len(log_entries(db, course_id))

    response = client.post(f"/courses/{course_id}/{move}", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Can't {move} this course: its status is {start}. From {start}, the only allowed move is {ONLY_MOVE_FROM[start]}."
    )
    assert status_in_database(db, course_id) == start
    assert len(log_entries(db, course_id)) == entries_before


# --- A published course needs a lesson -----------------------------------------------------------


def test_publishing_a_course_with_no_lessons_is_refused(client, db, headers):
    course_id, _ = create_course(client, headers)

    response = client.post(f"/courses/{course_id}/publish", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Can't publish this course: it has no lessons, and a published course needs at least one lesson."
    )
    assert status_in_database(db, course_id) == "draft"
    assert [entry.action for entry in log_entries(db, course_id)] == [Action.CREATED]


def test_restoring_a_course_with_no_lessons_is_refused(client, db, headers):
    # The app can't produce an archived course without lessons, so build one directly in the database.
    course_id, _ = create_course(client, headers, ["Alarms"])
    db.execute(delete(Lesson).where(Lesson.course_id == course_id))
    set_status(db, course_id, CourseStatus.ARCHIVED)
    entries_before = len(log_entries(db, course_id))

    response = client.post(f"/courses/{course_id}/restore", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Can't restore this course: it has no lessons, and a published course needs at least one lesson."
    )
    assert status_in_database(db, course_id) == "archived"
    assert len(log_entries(db, course_id)) == entries_before


# --- Who may move a course ------------------------------------------------------------------------


@pytest.mark.parametrize("move", ["publish", "archive", "restore"])
def test_learners_get_403_for_every_move_even_on_a_course_that_does_not_exist(
    client, db, make_user, auth_header, headers, move
):
    course_id, _ = create_course(client, headers, ["Alarms"])
    as_learner = auth_header(make_user(email="alex@example.com", role=Role.LEARNER))

    on_a_real_course = client.post(f"/courses/{course_id}/{move}", headers=as_learner)
    on_a_missing_course = client.post(f"/courses/999999/{move}", headers=as_learner)

    assert on_a_real_course.status_code == 403
    assert on_a_missing_course.status_code == 403
    assert status_in_database(db, course_id) == "draft"


@pytest.mark.parametrize("move", ["publish", "archive", "restore"])
def test_moving_a_course_that_does_not_exist_is_404(client, headers, move):
    response = client.post(f"/courses/999999/{move}", headers=headers)

    assert response.status_code == 404


def test_editing_a_course_never_changes_its_status(client, db, headers):
    course_id, _ = create_course(client, headers, ["Alarms"])
    body = {**FIRE_SAFETY, "title": "Fire drill", "status": "published"}

    response = client.put(f"/courses/{course_id}", json=body, headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Fire drill"
    assert response.json()["status"] == "draft"
    assert status_in_database(db, course_id) == "draft"


# --- Every change locks the course row first ------------------------------------------------------


@contextmanager
def recorded_sql():
    """Collect every SQL statement sent to the database while the block runs."""
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def first_index(statements, pattern):
    """Position of the first statement matching the regular expression, or None if none does."""
    for index, statement in enumerate(statements):
        if re.search(pattern, statement, re.IGNORECASE | re.DOTALL):
            return index
    return None


COURSE_LOCK = r"^\s*SELECT\b.*\bFROM courses\b.*\bFOR UPDATE\b"
COURSE_READ = r"^\s*SELECT\b.*\bFROM courses\b"
LESSON_READ = r"^\s*SELECT\b.*\bFROM lessons\b"
WRITE = r"^\s*(INSERT|UPDATE|DELETE)\b"


def send_change(client, headers, kind, course_id, lesson_ids):
    """Send one of the eight kinds of change to a course that has two lessons."""
    lessons_url = f"/courses/{course_id}/lessons"
    first_lesson, second_lesson = lesson_ids
    if kind in ("publish", "archive", "restore"):
        return client.post(f"/courses/{course_id}/{kind}", headers=headers)
    if kind == "edit course":
        return client.put(f"/courses/{course_id}", json={**FIRE_SAFETY, "title": "Fire drill"}, headers=headers)
    if kind == "add lesson":
        return client.post(lessons_url, json={"title": "Extinguishers", "content": "Text"}, headers=headers)
    if kind == "edit lesson":
        body = {"title": "Fire alarms", "content": "Text"}
        return client.put(f"{lessons_url}/{first_lesson}", json=body, headers=headers)
    if kind == "remove lesson":
        return client.delete(f"{lessons_url}/{second_lesson}", headers=headers)
    if kind == "reorder lessons":
        return client.put(f"{lessons_url}/order", json={"lesson_ids": [second_lesson, first_lesson]}, headers=headers)
    raise ValueError(f"unknown kind of change: {kind}")


@pytest.mark.parametrize(
    "kind, start",
    [
        ("publish", "draft"),
        ("archive", "published"),
        ("restore", "archived"),
        ("edit course", "draft"),
        ("add lesson", "draft"),
        ("edit lesson", "draft"),
        ("remove lesson", "draft"),
        ("reorder lessons", "draft"),
    ],
)
def test_every_change_locks_the_course_row_before_reading_or_writing(client, db, headers, kind, start):
    course_id, lesson_ids = create_course(client, headers, ["Alarms", "Exits"])
    set_status(db, course_id, start)

    with recorded_sql() as statements:
        response = send_change(client, headers, kind, course_id, lesson_ids)

    assert response.status_code in (200, 201, 204)
    lock = first_index(statements, COURSE_LOCK)
    first_write = first_index(statements, WRITE)
    first_lesson_read = first_index(statements, LESSON_READ)
    assert lock is not None, "the course row was never locked"
    assert first_write is not None and first_lesson_read is not None
    assert first_index(statements, COURSE_READ) == lock  # the first read of the course is the locking one
    assert lock < first_lesson_read
    assert lock < first_write


# --- Archived courses are read-only ---------------------------------------------------------------


@pytest.mark.parametrize("kind", ["edit course", "add lesson", "edit lesson", "remove lesson", "reorder lessons"])
def test_an_archived_course_cannot_be_changed(client, db, headers, kind):
    course_id, lesson_ids = create_course(client, headers, ["Alarms", "Exits"])
    set_status(db, course_id, CourseStatus.ARCHIVED)
    course_before = client.get(f"/courses/{course_id}", headers=headers).json()
    entries_before = len(log_entries(db, course_id))

    response = send_change(client, headers, kind, course_id, lesson_ids)

    assert response.status_code == 409
    assert response.json()["detail"] == "This course is archived, so it can't be changed. Restore it first."
    db.expire_all()  # read the course back from the database, not from cached objects
    assert client.get(f"/courses/{course_id}", headers=headers).json() == course_before
    assert len(log_entries(db, course_id)) == entries_before


# --- A published course keeps at least one lesson -------------------------------------------------


def test_the_last_lesson_of_a_published_course_cannot_be_removed(client, db, headers):
    course_id, [only_lesson] = create_course(client, headers, ["Alarms"])
    set_status(db, course_id, CourseStatus.PUBLISHED)
    entries_before = len(log_entries(db, course_id))

    response = client.delete(f"/courses/{course_id}/lessons/{only_lesson}", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A published course must keep at least one lesson. Add another lesson first, or archive the course."
    )
    db.expire_all()
    assert db.get(Lesson, only_lesson) is not None
    assert len(log_entries(db, course_id)) == entries_before


def test_the_last_lesson_of_a_draft_can_be_removed(client, headers):
    course_id, [only_lesson] = create_course(client, headers, ["Alarms"])

    response = client.delete(f"/courses/{course_id}/lessons/{only_lesson}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/courses/{course_id}", headers=headers).json()["lessons"] == []


def test_a_published_course_can_lose_a_lesson_while_another_remains(client, db, headers):
    course_id, [alarms, _exits] = create_course(client, headers, ["Alarms", "Exits"])
    set_status(db, course_id, CourseStatus.PUBLISHED)

    response = client.delete(f"/courses/{course_id}/lessons/{alarms}", headers=headers)

    assert response.status_code == 204
    course = client.get(f"/courses/{course_id}", headers=headers).json()
    assert course["status"] == "published"
    assert [(lesson["title"], lesson["position"]) for lesson in course["lessons"]] == [("Exits", 1)]
