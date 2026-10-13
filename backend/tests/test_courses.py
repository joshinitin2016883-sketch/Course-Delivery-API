"""Goal 2, courses: instructors create and edit courses; learners can't, and can't see drafts.
Every change writes an activity_log row in the same transaction as the change."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Action, ActivityLog, Course, CourseStatus, Role
from app.schemas.courses import CourseIn
from app.services import activity_log, course_service

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def instructor(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def learner(make_user):
    return make_user(email="alex@example.com", role=Role.LEARNER)


def post_course(client, headers):
    """Create the Fire safety course through the API and return its id."""
    response = client.post("/courses", json=FIRE_SAFETY, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def log_for(db, course_id):
    """The course's activity log, oldest first."""
    return list(db.scalars(select(ActivityLog).where(ActivityLog.course_id == course_id).order_by(ActivityLog.id)))


def count_courses(db):
    return db.scalar(select(func.count()).select_from(Course))


# --- Creating -------------------------------------------------------------------------------------


def test_instructor_creates_a_draft_course_and_it_is_logged(client, db, instructor, auth_header):
    response = client.post("/courses", json=FIRE_SAFETY, headers=auth_header(instructor))

    assert response.status_code == 201
    course = response.json()
    assert course["status"] == "draft"
    assert course["instructor"] == {"id": instructor.id, "full_name": "Priya Shah"}
    assert course["lessons"] == []
    [entry] = log_for(db, course["id"])
    assert entry.action == Action.CREATED
    assert entry.actor_id == instructor.id
    assert entry.details == FIRE_SAFETY


def test_a_new_course_is_a_draft_even_if_the_request_says_otherwise(client, instructor, auth_header):
    response = client.post("/courses", json={**FIRE_SAFETY, "status": "published"}, headers=auth_header(instructor))

    assert response.json()["status"] == "draft"


def test_learner_cannot_create_a_course(client, db, learner, auth_header):
    response = client.post("/courses", json=FIRE_SAFETY, headers=auth_header(learner))

    assert response.status_code == 403
    assert count_courses(db) == 0


def test_creating_a_course_requires_signing_in(client):
    response = client.post("/courses", json=FIRE_SAFETY)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {**FIRE_SAFETY, "title": "   "},
        {**FIRE_SAFETY, "description": ""},
        {**FIRE_SAFETY, "category": "cooking"},
        {**FIRE_SAFETY, "title": "x" * 201},
        {"title": "Fire safety", "description": "No category given."},
    ],
    ids=["blank title", "empty description", "unknown category", "title too long", "missing category"],
)
def test_invalid_course_details_are_rejected(client, db, instructor, auth_header, body):
    response = client.post("/courses", json=body, headers=auth_header(instructor))

    assert response.status_code == 422
    assert count_courses(db) == 0


def test_spaces_around_the_title_are_removed(client, instructor, auth_header):
    response = client.post("/courses", json={**FIRE_SAFETY, "title": "  Fire safety  "}, headers=auth_header(instructor))

    assert response.json()["title"] == "Fire safety"


# --- Viewing --------------------------------------------------------------------------------------


def test_any_instructor_can_open_any_course(client, make_user, instructor, auth_header):
    course_id = post_course(client, auth_header(instructor))
    colleague = make_user(email="daniel@example.com", role=Role.INSTRUCTOR)

    response = client.get(f"/courses/{course_id}", headers=auth_header(colleague))

    assert response.status_code == 200
    assert response.json()["title"] == "Fire safety"


def test_learner_gets_404_not_403_for_a_draft_course(client, instructor, learner, auth_header):
    course_id = post_course(client, auth_header(instructor))

    response = client.get(f"/courses/{course_id}", headers=auth_header(learner))

    # 404 rather than 403, so a learner can't even tell that the draft exists.
    assert response.status_code == 404


def test_learner_can_open_a_published_course(client, db, instructor, learner, auth_header):
    course_id = post_course(client, auth_header(instructor))
    # Publishing arrives in step 3, so set the status directly to test who may see a published course.
    db.get(Course, course_id).status = CourseStatus.PUBLISHED
    db.commit()

    response = client.get(f"/courses/{course_id}", headers=auth_header(learner))

    assert response.status_code == 200


def test_opening_a_course_that_does_not_exist_is_404(client, instructor, auth_header):
    response = client.get("/courses/999999", headers=auth_header(instructor))

    assert response.status_code == 404


# --- Editing --------------------------------------------------------------------------------------


def test_editing_saves_the_changes_and_logs_only_the_fields_that_changed(client, db, instructor, auth_header):
    course_id = post_course(client, auth_header(instructor))
    edited = {**FIRE_SAFETY, "title": "Fire safety 2026", "category": "skills"}

    response = client.put(f"/courses/{course_id}", json=edited, headers=auth_header(instructor))

    assert response.status_code == 200
    assert response.json()["title"] == "Fire safety 2026"
    assert response.json()["category"] == "skills"
    entry = log_for(db, course_id)[-1]
    assert entry.action == Action.EDITED
    assert entry.details == {
        "title": {"from": "Fire safety", "to": "Fire safety 2026"},
        "category": {"from": "compliance", "to": "skills"},
    }


def test_any_instructor_can_edit_any_course_and_the_log_names_who_did(client, db, make_user, instructor, auth_header):
    course_id = post_course(client, auth_header(instructor))
    colleague = make_user(email="daniel@example.com", role=Role.INSTRUCTOR)

    response = client.put(f"/courses/{course_id}", json={**FIRE_SAFETY, "title": "Fire drill"}, headers=auth_header(colleague))

    assert response.status_code == 200
    assert log_for(db, course_id)[-1].actor_id == colleague.id


def test_saving_a_course_without_changes_writes_no_log_row(client, db, instructor, auth_header):
    course_id = post_course(client, auth_header(instructor))

    response = client.put(f"/courses/{course_id}", json=FIRE_SAFETY, headers=auth_header(instructor))

    assert response.status_code == 200
    assert [entry.action for entry in log_for(db, course_id)] == [Action.CREATED]


def test_learner_cannot_edit_a_course(client, db, instructor, learner, auth_header):
    course_id = post_course(client, auth_header(instructor))

    response = client.put(f"/courses/{course_id}", json={**FIRE_SAFETY, "title": "Hacked"}, headers=auth_header(learner))

    assert response.status_code == 403
    assert client.get(f"/courses/{course_id}", headers=auth_header(instructor)).json()["title"] == "Fire safety"
    assert [entry.action for entry in log_for(db, course_id)] == [Action.CREATED]


def test_editing_a_course_that_does_not_exist_is_404(client, instructor, auth_header):
    response = client.put("/courses/999999", json=FIRE_SAFETY, headers=auth_header(instructor))

    assert response.status_code == 404


# --- The change and its log row are one transaction ------------------------------------------------


def test_a_course_is_not_saved_if_its_log_row_cannot_be_written(db, instructor, monkeypatch):
    def broken_record(*args):
        raise RuntimeError("could not write the log row")

    monkeypatch.setattr(activity_log, "record", broken_record)

    with pytest.raises(RuntimeError):
        course_service.create_course(db, instructor, CourseIn(**FIRE_SAFETY))
    db.rollback()  # what the request's session does when an error escapes

    assert count_courses(db) == 0


# --- What the database itself enforces ------------------------------------------------------------


@pytest.mark.parametrize(
    "field, value, constraint",
    [("status", "deleted", "ck_courses_status_allowed"), ("category", "cooking", "ck_courses_category_allowed")],
)
def test_database_rejects_an_unknown_status_or_category(db, instructor, field, value, constraint):
    course = Course(title="T", description="D", category="skills", instructor_id=instructor.id)
    setattr(course, field, value)
    db.add(course)

    with pytest.raises(IntegrityError, match=constraint):
        db.flush()
