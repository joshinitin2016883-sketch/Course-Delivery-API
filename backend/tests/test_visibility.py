"""Goals 1 and 5: what each person can see of a course.

Before enrolling, a learner sees a published course's title, description and lesson titles, but not the
lessons' content. An enrolled learner also sees the content and their own progress, and keeps read-only
access after the course is archived. Instructors see everything, including every learner's progress.
A learner never sees anyone else's progress.
"""
import pytest

from app.models import Role

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


def create_course(client, headers, lessons=2, status="published"):
    """Create a course with that many lessons and move it to that status. Returns the course id and lesson ids."""
    course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]
    lesson_ids = [
        client.post(
            f"/courses/{course_id}/lessons",
            json={"title": f"Lesson {number}", "content": f"Text for lesson {number}"},
            headers=headers,
        ).json()["id"]
        for number in range(1, lessons + 1)
    ]
    if status in ("published", "archived"):
        client.post(f"/courses/{course_id}/publish", headers=headers)
    if status == "archived":
        client.post(f"/courses/{course_id}/archive", headers=headers)
    return course_id, lesson_ids


def enroll(client, headers, course_id):
    response = client.post(f"/courses/{course_id}/enroll", headers=headers)
    assert response.status_code == 201


def complete(client, headers, course_id, lesson_id):
    return client.post(f"/courses/{course_id}/lessons/{lesson_id}/complete", headers=headers)


def open_course(client, headers, course_id):
    return client.get(f"/courses/{course_id}", headers=headers)


# --- Lesson content ------------------------------------------------------------------------------


def test_before_enrolling_a_learner_sees_the_lesson_titles_but_not_their_content(client, as_instructor, as_learner):
    course_id, _ = create_course(client, as_instructor, lessons=2)

    response = open_course(client, as_learner, course_id)

    assert response.status_code == 200
    page = response.json()
    assert (page["title"], page["description"]) == (FIRE_SAFETY["title"], FIRE_SAFETY["description"])
    assert [(lesson["title"], lesson["content"]) for lesson in page["lessons"]] == [("Lesson 1", None), ("Lesson 2", None)]
    assert page["my_progress"] is None


def test_after_enrolling_a_learner_sees_the_content_and_their_own_progress(client, as_instructor, as_learner):
    course_id, [first, _second] = create_course(client, as_instructor, lessons=2)
    enroll(client, as_learner, course_id)
    complete(client, as_learner, course_id, first)

    page = open_course(client, as_learner, course_id).json()

    assert [lesson["content"] for lesson in page["lessons"]] == ["Text for lesson 1", "Text for lesson 2"]
    progress = page["my_progress"]
    assert (progress["status"], progress["lessons_done"], progress["lessons_total"]) == ("in_progress", 1, 2)
    assert progress["completed_lesson_ids"] == [first]


def test_instructors_see_the_content_and_no_progress_of_their_own(client, as_instructor):
    course_id, _ = create_course(client, as_instructor, lessons=2)

    page = open_course(client, as_instructor, course_id).json()

    assert [lesson["content"] for lesson in page["lessons"]] == ["Text for lesson 1", "Text for lesson 2"]
    assert page["my_progress"] is None


# --- Archived courses -----------------------------------------------------------------------------


def test_an_enrolled_learner_can_still_open_a_course_after_it_is_archived(client, as_instructor, as_learner):
    course_id, [first, _second] = create_course(client, as_instructor, lessons=2)
    enroll(client, as_learner, course_id)
    complete(client, as_learner, course_id, first)
    client.post(f"/courses/{course_id}/archive", headers=as_instructor)

    response = open_course(client, as_learner, course_id)

    assert response.status_code == 200
    page = response.json()
    assert page["status"] == "archived"
    assert page["lessons"][0]["content"] == "Text for lesson 1"
    assert page["my_progress"]["lessons_done"] == 1


def test_completing_a_lesson_in_an_archived_course_gives_409(client, as_instructor, as_learner):
    course_id, [first, second] = create_course(client, as_instructor, lessons=2)
    enroll(client, as_learner, course_id)
    complete(client, as_learner, course_id, first)
    client.post(f"/courses/{course_id}/archive", headers=as_instructor)

    response = complete(client, as_learner, course_id, second)

    assert response.status_code == 409
    assert response.json()["detail"] == "This course is archived, so you can't complete lessons in it any more."
    assert open_course(client, as_learner, course_id).json()["my_progress"]["lessons_done"] == 1


def test_a_learner_who_is_not_enrolled_gets_the_same_404_for_an_archived_course_as_a_missing_one(
    client, as_instructor, as_learner
):
    course_id, _ = create_course(client, as_instructor, status="archived")

    archived = open_course(client, as_learner, course_id)
    missing = open_course(client, as_learner, 999999)

    assert archived.status_code == missing.status_code == 404
    assert archived.json() == missing.json()


def test_enrolling_again_in_a_course_archived_since_is_409_already_enrolled(client, as_instructor, as_learner):
    course_id, _ = create_course(client, as_instructor)
    enroll(client, as_learner, course_id)
    client.post(f"/courses/{course_id}/archive", headers=as_instructor)

    response = client.post(f"/courses/{course_id}/enroll", headers=as_learner)

    assert response.status_code == 409
    assert response.json()["detail"] == "You are already enrolled in this course."


# --- Everyone's progress, for instructors ---------------------------------------------------------


def test_instructors_see_every_enrolled_learners_progress(client, make_user, auth_header, as_instructor, as_learner):
    course_id, [first, second] = create_course(client, as_instructor, lessons=2)
    as_sam = auth_header(make_user(email="sam@example.com", role=Role.LEARNER, full_name="Sam Taylor"))
    enroll(client, as_learner, course_id)
    enroll(client, as_sam, course_id)
    complete(client, as_learner, course_id, first)
    complete(client, as_sam, course_id, first)
    complete(client, as_sam, course_id, second)

    response = client.get(f"/courses/{course_id}/progress", headers=as_instructor)

    assert response.status_code == 200
    rows = response.json()
    summary = [
        (row["learner"]["full_name"], row["learner"]["email"], row["status"], row["lessons_done"], row["lessons_total"])
        for row in rows
    ]
    assert summary == [
        ("Alex Chen", "alex@example.com", "in_progress", 1, 2),
        ("Sam Taylor", "sam@example.com", "completed", 2, 2),
    ]
    assert all(row["enrolled_at"] and row["started_at"] and row["last_activity_at"] for row in rows)
    assert (rows[0]["completed_at"] is None) and (rows[1]["completed_at"] is not None)


def test_learners_get_403_for_the_progress_list_even_for_a_course_that_does_not_exist(
    client, as_instructor, as_learner
):
    course_id, _ = create_course(client, as_instructor)
    enroll(client, as_learner, course_id)

    on_a_real_course = client.get(f"/courses/{course_id}/progress", headers=as_learner)
    on_a_missing_course = client.get("/courses/999999/progress", headers=as_learner)

    assert on_a_real_course.status_code == 403
    assert on_a_missing_course.status_code == 403


def test_the_progress_list_of_a_course_that_does_not_exist_is_404(client, as_instructor):
    response = client.get("/courses/999999/progress", headers=as_instructor)

    assert response.status_code == 404


# --- Nobody else's progress -----------------------------------------------------------------------


def test_a_learner_never_sees_another_learners_progress(client, make_user, auth_header, as_instructor, as_learner):
    course_id, [first, second] = create_course(client, as_instructor, lessons=2)
    as_sam = auth_header(make_user(email="sam@example.com", role=Role.LEARNER, full_name="Sam Taylor"))
    enroll(client, as_learner, course_id)
    enroll(client, as_sam, course_id)
    complete(client, as_sam, course_id, first)
    complete(client, as_sam, course_id, second)  # Sam finishes; Alex hasn't started

    page = open_course(client, as_learner, course_id).json()
    my_courses = client.get("/me/courses", headers=as_learner).json()
    progress_list = client.get(f"/courses/{course_id}/progress", headers=as_learner)
    feed = client.get(f"/courses/{course_id}/activity", headers=as_learner).json()

    assert (page["my_progress"]["status"], page["my_progress"]["completed_lesson_ids"]) == ("not_started", [])
    assert [(entry["status"], entry["lessons_done"]) for entry in my_courses] == [("not_started", 0)]
    assert progress_list.status_code == 403
    assert feed == []  # a learner's feed holds only comments, and progress is never written to the log
