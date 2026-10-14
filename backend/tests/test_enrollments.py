"""Goal 5, enrolment: learners enrol themselves in published courses and see one list of all their courses.
(Completing lessons comes with the next change.)"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Enrollment, EnrollmentStatus, Role

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def instructor(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def learner(make_user):
    return make_user(email="alex@example.com", role=Role.LEARNER, full_name="Alex Chen")


@pytest.fixture
def as_instructor(instructor, auth_header):
    return auth_header(instructor)


@pytest.fixture
def as_learner(learner, auth_header):
    return auth_header(learner)


def create_course(client, headers, title="Fire safety", lessons=1, status="published"):
    """Create a course with that many lessons and move it to that status, through the API. Returns its id."""
    course_id = client.post("/courses", json={**FIRE_SAFETY, "title": title}, headers=headers).json()["id"]
    for number in range(1, lessons + 1):
        lesson = {"title": f"Lesson {number}", "content": "Text"}
        client.post(f"/courses/{course_id}/lessons", json=lesson, headers=headers)
    if status in ("published", "archived"):
        client.post(f"/courses/{course_id}/publish", headers=headers)
    if status == "archived":
        client.post(f"/courses/{course_id}/archive", headers=headers)
    return course_id


def enroll(client, headers, course_id):
    return client.post(f"/courses/{course_id}/enroll", headers=headers)


def enrollment_rows(db, course_id):
    return db.scalars(select(Enrollment).where(Enrollment.course_id == course_id)).all()


# --- Enrolling ------------------------------------------------------------------------------------


def test_a_learner_enrols_in_a_published_course(client, db, learner, as_instructor, as_learner):
    course_id = create_course(client, as_instructor, lessons=2)

    response = enroll(client, as_learner, course_id)

    assert response.status_code == 201
    enrolment = response.json()
    assert enrolment["course"] == {"id": course_id, "title": "Fire safety", "category": "compliance", "status": "published"}
    assert enrolment["status"] == "not_started"
    assert (enrolment["lessons_done"], enrolment["lessons_total"]) == (0, 2)
    assert enrolment["enrolled_at"] is not None
    assert (enrolment["started_at"], enrolment["completed_at"], enrolment["last_activity_at"]) == (None, None, None)
    [row] = enrollment_rows(db, course_id)
    assert (row.user_id, row.enrolled_by, row.status) == (learner.id, learner.id, EnrollmentStatus.NOT_STARTED)


def test_draft_archived_and_missing_courses_give_the_same_404(client, db, as_instructor, as_learner):
    draft = create_course(client, as_instructor, status="draft")
    archived = create_course(client, as_instructor, status="archived")

    responses = [enroll(client, as_learner, course_id) for course_id in (draft, archived, 999999)]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert responses[0].json() == responses[1].json() == responses[2].json()
    assert enrollment_rows(db, draft) == enrollment_rows(db, archived) == []


def test_enrolling_twice_gives_409_and_leaves_one_row(client, db, as_instructor, as_learner):
    course_id = create_course(client, as_instructor)
    enroll(client, as_learner, course_id)

    response = enroll(client, as_learner, course_id)

    assert response.status_code == 409
    assert response.json()["detail"] == "You are already enrolled in this course."
    assert len(enrollment_rows(db, course_id)) == 1


def test_instructors_get_403_even_for_a_course_that_does_not_exist(client, db, as_instructor):
    course_id = create_course(client, as_instructor)

    on_a_real_course = enroll(client, as_instructor, course_id)
    on_a_missing_course = enroll(client, as_instructor, 999999)

    assert on_a_real_course.status_code == 403
    assert on_a_missing_course.status_code == 403
    assert enrollment_rows(db, course_id) == []


COURSE_SHARE_LOCK = r"^\s*SELECT\b.*\bFROM courses\b.*\bFOR SHARE\b"
COURSE_READ = r"^\s*SELECT\b.*\bFROM courses\b"
ENROLLMENT_INSERT = r"^\s*INSERT INTO enrollments\b"


def test_enrolling_takes_a_shared_lock_on_the_course_before_writing(
    client, as_instructor, as_learner, recorded_sql, first_index
):
    course_id = create_course(client, as_instructor)

    with recorded_sql() as statements:
        response = enroll(client, as_learner, course_id)

    assert response.status_code == 201
    lock = first_index(statements, COURSE_SHARE_LOCK)
    assert lock is not None, "the course row was never locked"
    assert first_index(statements, COURSE_READ) == lock  # the first read of the course is the locking one
    assert lock < first_index(statements, ENROLLMENT_INSERT)


# --- My courses -----------------------------------------------------------------------------------


def test_my_courses_lists_every_enrolment_newest_first_with_archived_ones_marked(client, as_instructor, as_learner):
    fire_safety = create_course(client, as_instructor, title="Fire safety", lessons=2)
    data_protection = create_course(client, as_instructor, title="Data protection", lessons=3)
    enroll(client, as_learner, fire_safety)
    enroll(client, as_learner, data_protection)
    client.post(f"/courses/{fire_safety}/archive", headers=as_instructor)

    response = client.get("/me/courses", headers=as_learner)

    assert response.status_code == 200
    summary = [
        (entry["course"]["title"], entry["course"]["status"], entry["status"], entry["lessons_done"], entry["lessons_total"])
        for entry in response.json()
    ]
    assert summary == [
        ("Data protection", "published", "not_started", 0, 3),
        ("Fire safety", "archived", "not_started", 0, 2),
    ]


def test_my_courses_shows_only_my_own_enrolments(client, make_user, auth_header, as_instructor, as_learner):
    fire_safety = create_course(client, as_instructor, title="Fire safety")
    data_protection = create_course(client, as_instructor, title="Data protection")
    enroll(client, as_learner, fire_safety)
    someone_else = auth_header(make_user(email="sam@example.com", role=Role.LEARNER))
    enroll(client, someone_else, data_protection)

    response = client.get("/me/courses", headers=as_learner)

    assert [entry["course"]["id"] for entry in response.json()] == [fire_safety]


def test_instructors_get_403_for_my_courses(client, as_instructor):
    response = client.get("/me/courses", headers=as_instructor)

    assert response.status_code == 403


def test_my_courses_takes_the_same_number_of_queries_however_many_courses(
    client, db, as_instructor, as_learner, recorded_sql
):
    def queries_after_enrolling_in(new_courses):
        for _ in range(new_courses):
            enroll(client, as_learner, create_course(client, as_instructor))
        db.expunge_all()  # empty the session's cache, so everything has to come from the database
        with recorded_sql() as statements:
            response = client.get("/me/courses", headers=as_learner)
        assert response.status_code == 200
        return len(statements)

    assert queries_after_enrolling_in(1) == queries_after_enrolling_in(3)  # 1 course, then 4


# --- What the database itself enforces ------------------------------------------------------------


def test_the_database_refuses_a_second_enrolment_for_the_same_learner_and_course(client, db, learner, as_instructor):
    course_id = create_course(client, as_instructor)
    db.add_all(Enrollment(course_id=course_id, user_id=learner.id, enrolled_by=learner.id) for _ in range(2))

    with pytest.raises(IntegrityError, match="uq_enrollments_course_id_user_id"):
        db.flush()


NOW = datetime.now(timezone.utc)


@pytest.mark.parametrize(
    "fields, constraint",
    [
        # Each row breaks exactly one check, so the error names that check.
        ({"status": "paused", "started_at": NOW, "last_activity_at": NOW}, "ck_enrollments_status_allowed"),
        (
            {"status": "completed", "started_at": NOW, "last_activity_at": NOW},  # no completed_at
            "ck_enrollments_completed_matches_completed_at",
        ),
        (
            {"status": "not_started", "started_at": NOW, "last_activity_at": NOW},
            "ck_enrollments_not_started_matches_started_at",
        ),
        ({"status": "in_progress", "started_at": NOW}, "ck_enrollments_started_matches_last_activity"),
    ],
    ids=["unknown status", "completed without completed_at", "not started with started_at", "started, no last activity"],
)
def test_the_database_refuses_an_enrolment_whose_status_and_times_disagree(
    client, db, learner, as_instructor, fields, constraint
):
    course_id = create_course(client, as_instructor)
    db.add(Enrollment(course_id=course_id, user_id=learner.id, enrolled_by=learner.id, **fields))

    with pytest.raises(IntegrityError, match=constraint):
        db.flush()


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"status": "in_progress", "started_at": NOW, "last_activity_at": NOW},
        {"status": "completed", "started_at": NOW, "completed_at": NOW, "last_activity_at": NOW},
    ],
    ids=["not started", "in progress", "completed"],
)
def test_the_database_accepts_an_enrolment_whose_status_and_times_agree(client, db, learner, as_instructor, fields):
    course_id = create_course(client, as_instructor)
    db.add(Enrollment(course_id=course_id, user_id=learner.id, enrolled_by=learner.id, **fields))

    db.flush()  # raises IntegrityError if a check wrongly refuses a valid row
