"""Goal 9, history you cannot rewrite: every change to a course adds a log row naming who made it,
and the database refuses to change or delete log rows afterwards, no matter who asks."""
import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.models import Action, ActivityLog, Role

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def course_id(client, make_user, auth_header):
    instructor = make_user(email="priya@example.com", role=Role.INSTRUCTOR)
    return client.post("/courses", json=FIRE_SAFETY, headers=auth_header(instructor)).json()["id"]


def test_every_change_to_a_course_adds_one_log_row_naming_who_made_it(client, db, make_user, auth_header):
    priya = make_user(email="priya@example.com", role=Role.INSTRUCTOR)
    daniel = make_user(email="daniel@example.com", role=Role.INSTRUCTOR)
    as_priya, as_daniel = auth_header(priya), auth_header(daniel)

    course_id = client.post("/courses", json=FIRE_SAFETY, headers=as_priya).json()["id"]
    client.put(f"/courses/{course_id}", json={**FIRE_SAFETY, "title": "Fire safety 2026"}, headers=as_daniel)
    lessons_url = f"/courses/{course_id}/lessons"
    alarms = client.post(lessons_url, json={"title": "Alarms", "content": "Text"}, headers=as_priya).json()["id"]
    exits = client.post(lessons_url, json={"title": "Exits", "content": "Text"}, headers=as_priya).json()["id"]
    client.put(f"{lessons_url}/{alarms}", json={"title": "Fire alarms", "content": "Text"}, headers=as_daniel)
    client.put(f"{lessons_url}/order", json={"lesson_ids": [exits, alarms]}, headers=as_priya)
    client.delete(f"{lessons_url}/{alarms}", headers=as_daniel)

    log = db.scalars(select(ActivityLog).where(ActivityLog.course_id == course_id).order_by(ActivityLog.id)).all()
    assert [(entry.action, entry.actor_id) for entry in log] == [
        (Action.CREATED, priya.id),
        (Action.EDITED, daniel.id),
        (Action.LESSON_ADDED, priya.id),
        (Action.LESSON_ADDED, priya.id),
        (Action.LESSON_EDITED, daniel.id),
        (Action.LESSONS_REORDERED, priya.id),
        (Action.LESSON_REMOVED, daniel.id),
    ]
    assert all(entry.created_at is not None for entry in log)


# The app has no code that edits or deletes log rows. These tests go around the app and talk
# to the database directly, to show the trigger from migration 0002 refuses even then.


def test_the_database_refuses_to_change_a_log_row(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(update(ActivityLog).where(ActivityLog.course_id == course_id).values(action="edited"))


def test_the_database_refuses_to_delete_a_log_row(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(delete(ActivityLog).where(ActivityLog.course_id == course_id))


def test_the_database_refuses_to_empty_the_log(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("TRUNCATE activity_log"))
