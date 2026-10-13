"""Goal 3, lessons: instructors add, edit, reorder and remove them, and a course shows them in order.
Positions always run 1, 2, 3, ... and every change is logged against the course."""
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Action, ActivityLog, Lesson, Role
from app.schemas.lessons import LessonIn
from app.services import activity_log, lesson_service

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def instructor(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR)


@pytest.fixture
def headers(instructor, auth_header):
    return auth_header(instructor)


@pytest.fixture
def course_id(client, headers):
    return client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]


def add_lesson(client, headers, course_id, title):
    """Add a lesson through the API and return its id."""
    response = client.post(
        f"/courses/{course_id}/lessons", json={"title": title, "content": f"All about {title}."}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def lessons_shown(client, headers, course_id):
    """(title, position) of each lesson, in the order opening the course shows them."""
    lessons = client.get(f"/courses/{course_id}", headers=headers).json()["lessons"]
    return [(lesson["title"], lesson["position"]) for lesson in lessons]


def last_log_entry(db, course_id):
    return db.scalars(
        select(ActivityLog).where(ActivityLog.course_id == course_id).order_by(ActivityLog.id.desc())
    ).first()


# --- Adding and viewing ---------------------------------------------------------------------------


def test_new_lessons_go_to_the_end_and_the_course_shows_them_in_order(client, headers, course_id):
    add_lesson(client, headers, course_id, "Alarms")
    add_lesson(client, headers, course_id, "Exits")
    add_lesson(client, headers, course_id, "Extinguishers")

    assert lessons_shown(client, headers, course_id) == [("Alarms", 1), ("Exits", 2), ("Extinguishers", 3)]


def test_adding_a_lesson_is_logged_with_its_title_and_position(client, db, instructor, headers, course_id):
    lesson_id = add_lesson(client, headers, course_id, "Alarms")

    entry = last_log_entry(db, course_id)
    assert entry.action == Action.LESSON_ADDED
    assert entry.actor_id == instructor.id
    assert entry.details == {"lesson_id": lesson_id, "title": "Alarms", "position": 1}


def test_adding_a_lesson_to_a_course_that_does_not_exist_is_404(client, headers):
    response = client.post("/courses/999999/lessons", json={"title": "Alarms", "content": "Text"}, headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"title": "   ", "content": "Text"}, {"title": "Alarms", "content": ""}, {"title": "Alarms"}],
    ids=["blank title", "empty content", "missing content"],
)
def test_invalid_lesson_details_are_rejected(client, headers, course_id, body):
    response = client.post(f"/courses/{course_id}/lessons", json=body, headers=headers)

    assert response.status_code == 422
    assert lessons_shown(client, headers, course_id) == []


# --- Editing --------------------------------------------------------------------------------------


def test_editing_a_lesson_logs_only_what_changed(client, db, headers, course_id):
    lesson_id = add_lesson(client, headers, course_id, "Alarms")

    response = client.put(
        f"/courses/{course_id}/lessons/{lesson_id}",
        json={"title": "Fire alarms", "content": "All about Alarms."},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Fire alarms"
    entry = last_log_entry(db, course_id)
    assert entry.action == Action.LESSON_EDITED
    assert entry.details == {
        "lesson_id": lesson_id,
        "title": "Fire alarms",
        "changes": {"title": {"from": "Alarms", "to": "Fire alarms"}},
    }


def test_saving_a_lesson_without_changes_writes_no_log_row(client, db, headers, course_id):
    lesson_id = add_lesson(client, headers, course_id, "Alarms")
    last_entry_before = last_log_entry(db, course_id).id

    response = client.put(
        f"/courses/{course_id}/lessons/{lesson_id}",
        json={"title": "Alarms", "content": "All about Alarms."},
        headers=headers,
    )

    assert response.status_code == 200
    assert last_log_entry(db, course_id).id == last_entry_before


def test_a_lesson_can_only_be_changed_through_its_own_course(client, headers, course_id):
    lesson_id = add_lesson(client, headers, course_id, "Alarms")
    other_course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]

    edit = client.put(
        f"/courses/{other_course_id}/lessons/{lesson_id}", json={"title": "Moved", "content": "x"}, headers=headers
    )
    remove = client.delete(f"/courses/{other_course_id}/lessons/{lesson_id}", headers=headers)

    assert edit.status_code == 404
    assert remove.status_code == 404
    assert lessons_shown(client, headers, course_id) == [("Alarms", 1)]


# --- Removing -------------------------------------------------------------------------------------


def test_removing_a_lesson_closes_the_gap_and_the_log_keeps_its_title(client, db, headers, course_id):
    add_lesson(client, headers, course_id, "Alarms")
    exits_id = add_lesson(client, headers, course_id, "Exits")
    add_lesson(client, headers, course_id, "Extinguishers")

    response = client.delete(f"/courses/{course_id}/lessons/{exits_id}", headers=headers)

    assert response.status_code == 204
    assert lessons_shown(client, headers, course_id) == [("Alarms", 1), ("Extinguishers", 2)]
    assert db.get(Lesson, exits_id) is None
    entry = last_log_entry(db, course_id)
    assert entry.action == Action.LESSON_REMOVED
    assert entry.details == {"lesson_id": exits_id, "title": "Exits", "position": 2}


# --- Reordering -----------------------------------------------------------------------------------


def test_reordering_puts_the_lessons_in_the_new_order_and_logs_it_once(client, db, headers, course_id):
    alarms = add_lesson(client, headers, course_id, "Alarms")
    exits = add_lesson(client, headers, course_id, "Exits")
    extinguishers = add_lesson(client, headers, course_id, "Extinguishers")
    last_entry_before = last_log_entry(db, course_id).id

    response = client.put(
        f"/courses/{course_id}/lessons/order", json={"lesson_ids": [extinguishers, alarms, exits]}, headers=headers
    )

    assert response.status_code == 200
    assert [lesson["title"] for lesson in response.json()] == ["Extinguishers", "Alarms", "Exits"]
    assert lessons_shown(client, headers, course_id) == [("Extinguishers", 1), ("Alarms", 2), ("Exits", 3)]
    entry = last_log_entry(db, course_id)
    assert entry.action == Action.LESSONS_REORDERED
    assert entry.details == {"from": [alarms, exits, extinguishers], "to": [extinguishers, alarms, exits]}
    entries_since = db.scalars(
        select(ActivityLog).where(ActivityLog.course_id == course_id, ActivityLog.id > last_entry_before)
    ).all()
    assert len(entries_since) == 1


def test_a_new_order_must_list_every_lesson_of_the_course_exactly_once(client, db, headers, course_id):
    alarms = add_lesson(client, headers, course_id, "Alarms")
    exits = add_lesson(client, headers, course_id, "Exits")
    other_course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]
    elsewhere = add_lesson(client, headers, other_course_id, "Elsewhere")
    bad_orders = {
        "a lesson left out": [alarms],
        "a lesson from another course": [alarms, exits, elsewhere],
        "a lesson listed twice": [alarms, exits, exits],
        "an id that doesn't exist": [alarms, 999999],
    }

    for problem, order in bad_orders.items():
        response = client.put(f"/courses/{course_id}/lessons/order", json={"lesson_ids": order}, headers=headers)
        assert response.status_code == 409, problem

    assert lessons_shown(client, headers, course_id) == [("Alarms", 1), ("Exits", 2)]
    assert last_log_entry(db, course_id).action == Action.LESSON_ADDED  # the rejected attempts logged nothing


def test_reordering_into_the_same_order_writes_no_log_row(client, db, headers, course_id):
    alarms = add_lesson(client, headers, course_id, "Alarms")
    exits = add_lesson(client, headers, course_id, "Exits")
    last_entry_before = last_log_entry(db, course_id).id

    response = client.put(f"/courses/{course_id}/lessons/order", json={"lesson_ids": [alarms, exits]}, headers=headers)

    assert response.status_code == 200
    assert last_log_entry(db, course_id).id == last_entry_before


# --- Learners ------------------------------------------------------------------------------------


def test_learners_cannot_add_edit_reorder_or_remove_lessons(client, make_user, auth_header, headers, course_id):
    lesson_id = add_lesson(client, headers, course_id, "Alarms")
    as_learner = auth_header(make_user(email="alex@example.com", role=Role.LEARNER))
    lesson = {"title": "Changed", "content": "Changed"}

    responses = [
        client.post(f"/courses/{course_id}/lessons", json=lesson, headers=as_learner),
        client.put(f"/courses/{course_id}/lessons/{lesson_id}", json=lesson, headers=as_learner),
        client.put(f"/courses/{course_id}/lessons/order", json={"lesson_ids": [lesson_id]}, headers=as_learner),
        client.delete(f"/courses/{course_id}/lessons/{lesson_id}", headers=as_learner),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert lessons_shown(client, headers, course_id) == [("Alarms", 1)]


# --- The change and its log row are one transaction ------------------------------------------------


def test_a_lesson_is_not_saved_if_its_log_row_cannot_be_written(db, instructor, course_id, monkeypatch):
    def broken_record(*args):
        raise RuntimeError("could not write the log row")

    monkeypatch.setattr(activity_log, "record", broken_record)

    with pytest.raises(RuntimeError):
        lesson_service.add_lesson(db, instructor, course_id, LessonIn(title="Alarms", content="Text"))
    db.rollback()  # what the request's session does when an error escapes

    assert db.scalars(select(Lesson).where(Lesson.course_id == course_id)).all() == []


# --- What the database itself enforces ------------------------------------------------------------


def test_database_rejects_two_lessons_in_the_same_position(db, course_id):
    # The real check waits until commit (so renumbering works); ask Postgres to check each statement instead.
    db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    db.add_all(
        [
            Lesson(course_id=course_id, title="A", content="a", position=1),
            Lesson(course_id=course_id, title="B", content="b", position=1),
        ]
    )

    with pytest.raises(IntegrityError, match="uq_lessons_course_id_position"):
        db.flush()


def test_database_rejects_a_position_below_1(db, course_id):
    db.add(Lesson(course_id=course_id, title="A", content="a", position=0))

    with pytest.raises(IntegrityError, match="ck_lessons_position_positive"):
        db.flush()
