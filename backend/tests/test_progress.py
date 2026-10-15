"""Goal 4, learner progress: completing lessons moves a learner Not started -> In progress -> Completed.

The server works the state out from the lessons completed; nothing sets it by hand. A lesson that any
learner has completed can't be removed, and removing a lesson finishes the course for learners who had
already done every other lesson.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.models import ActivityLog, Enrollment, EnrollmentStatus, Lesson, LessonCompletion, Role
from app.services import enrollment_service

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


def create_course(client, headers, lessons=3, status="published"):
    """Create a course with that many lessons and move it to that status. Returns the course id and lesson ids."""
    course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]
    lesson_ids = [
        client.post(
            f"/courses/{course_id}/lessons", json={"title": f"Lesson {number}", "content": "Text"}, headers=headers
        ).json()["id"]
        for number in range(1, lessons + 1)
    ]
    if status in ("published", "archived"):
        client.post(f"/courses/{course_id}/publish", headers=headers)
    if status == "archived":
        client.post(f"/courses/{course_id}/archive", headers=headers)
    return course_id, lesson_ids


def enrolled_course(client, as_instructor, as_learner, lessons=3):
    """A published course the learner has enrolled in. Returns the course id and lesson ids."""
    course_id, lesson_ids = create_course(client, as_instructor, lessons)
    client.post(f"/courses/{course_id}/enroll", headers=as_learner)
    return course_id, lesson_ids


def complete(client, headers, course_id, lesson_id):
    return client.post(f"/courses/{course_id}/lessons/{lesson_id}/complete", headers=headers)


def enrollment_of(db, user, course_id):
    db.expire_all()  # forget cached objects, so this reads the database
    return db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id))


def count_log_rows(db, course_id):
    return db.scalar(select(func.count()).select_from(ActivityLog).where(ActivityLog.course_id == course_id))


# --- Moving through the states --------------------------------------------------------------------


def test_completing_lessons_moves_not_started_to_in_progress_to_completed(client, as_instructor, as_learner):
    course_id, [first, second, third] = enrolled_course(client, as_instructor, as_learner, lessons=3)

    responses = [complete(client, as_learner, course_id, lesson) for lesson in (first, second, third)]

    assert [response.status_code for response in responses] == [200, 200, 200]
    after_first, after_second, after_third = [response.json() for response in responses]
    assert [(p["status"], p["lessons_done"], p["lessons_total"]) for p in (after_first, after_second, after_third)] == [
        ("in_progress", 1, 3),
        ("in_progress", 2, 3),
        ("completed", 3, 3),
    ]
    assert after_first["started_at"] is not None and after_first["completed_at"] is None
    assert after_third["started_at"] == after_first["started_at"]  # started once, at the first completion
    assert after_third["completed_at"] is not None
    assert after_third["completed_lesson_ids"] == sorted([first, second, third])


def test_a_one_lesson_course_goes_through_both_moves_in_one_request(client, as_instructor, as_learner):
    course_id, [only_lesson] = enrolled_course(client, as_instructor, as_learner, lessons=1)

    response = complete(client, as_learner, course_id, only_lesson)

    assert response.status_code == 200
    progress = response.json()
    assert (progress["status"], progress["lessons_done"], progress["lessons_total"]) == ("completed", 1, 1)
    assert progress["started_at"] is not None and progress["completed_at"] is not None


def test_a_completion_and_the_enrolment_share_one_timestamp(client, db, learner, as_instructor, as_learner):
    # The enrolment's times copy its completions' times, so they must be the same instant, not two clocks
    # a few milliseconds apart.
    course_id, [first, second] = enrolled_course(client, as_instructor, as_learner, lessons=2)

    complete(client, as_learner, course_id, first)
    enrollment = enrollment_of(db, learner, course_id)
    first_done = completed_at(db, enrollment, first)
    assert enrollment.started_at == enrollment.last_activity_at == first_done

    complete(client, as_learner, course_id, second)  # the last lesson, so this finishes the course
    enrollment = enrollment_of(db, learner, course_id)
    assert enrollment.last_activity_at == enrollment.completed_at == completed_at(db, enrollment, second)
    assert enrollment.started_at == first_done


def completed_at(db, enrollment, lesson_id):
    return db.scalar(
        select(LessonCompletion.completed_at).where(
            LessonCompletion.enrollment_id == enrollment.id, LessonCompletion.lesson_id == lesson_id
        )
    )


def test_completing_a_lesson_twice_changes_nothing(client, db, learner, as_instructor, as_learner):
    course_id, [first, _second, _third] = enrolled_course(client, as_instructor, as_learner)
    first_time = complete(client, as_learner, course_id, first).json()

    second_time = complete(client, as_learner, course_id, first)

    assert second_time.status_code == 200
    assert second_time.json() == first_time
    enrollment = enrollment_of(db, learner, course_id)
    assert db.scalar(
        select(func.count()).select_from(LessonCompletion).where(LessonCompletion.enrollment_id == enrollment.id)
    ) == 1


def test_a_lesson_added_after_completion_leaves_the_learner_completed(client, as_instructor, as_learner):
    course_id, [only_lesson] = enrolled_course(client, as_instructor, as_learner, lessons=1)
    when_completed = complete(client, as_learner, course_id, only_lesson).json()
    new_lesson = {"title": "Lesson 2", "content": "Text"}
    new_lesson_id = client.post(f"/courses/{course_id}/lessons", json=new_lesson, headers=as_instructor).json()["id"]

    [my_course] = client.get("/me/courses", headers=as_learner).json()
    assert (my_course["status"], my_course["lessons_done"], my_course["lessons_total"]) == ("completed", 1, 2)

    # Completing the new lesson is recorded, but the learner was already Completed, so the state doesn't move.
    after = complete(client, as_learner, course_id, new_lesson_id).json()
    assert (after["status"], after["lessons_done"], after["lessons_total"]) == ("completed", 2, 2)
    assert after["completed_at"] == when_completed["completed_at"]
    assert datetime.fromisoformat(after["last_activity_at"]) > datetime.fromisoformat(when_completed["last_activity_at"])


# --- The table of progress moves ------------------------------------------------------------------


@pytest.mark.parametrize("start, target", [("not_started", "in_progress"), ("in_progress", "completed")])
def test_the_two_forward_moves_are_allowed(start, target):
    enrollment = Enrollment(status=start)

    enrollment_service._move(enrollment, target, datetime.now(timezone.utc))

    assert enrollment.status == target


@pytest.mark.parametrize(
    "start, target",
    [
        ("not_started", "not_started"),
        ("not_started", "completed"),
        ("in_progress", "not_started"),
        ("in_progress", "in_progress"),
        ("completed", "not_started"),
        ("completed", "in_progress"),
        ("completed", "completed"),
    ],
)
def test_every_other_progress_move_is_refused(start, target):
    enrollment = Enrollment(status=start)

    with pytest.raises(RuntimeError, match="Illegal progress move"):
        enrollment_service._move(enrollment, target, datetime.now(timezone.utc))
    assert enrollment.status == start


# --- Who can complete what ------------------------------------------------------------------------


def test_instructors_get_403_even_for_a_course_that_does_not_exist(client, as_instructor):
    course_id, [first, *_] = create_course(client, as_instructor)

    assert complete(client, as_instructor, course_id, first).status_code == 403
    assert complete(client, as_instructor, 999999, first).status_code == 403


def test_a_learner_who_is_not_enrolled_gets_403(client, as_instructor, as_learner):
    course_id, [first, *_] = create_course(client, as_instructor)

    response = complete(client, as_learner, course_id, first)

    assert response.status_code == 403
    assert response.json()["detail"] == "Enrol in this course first."


def test_a_course_the_learner_cannot_see_gives_the_same_404_as_a_missing_one(client, as_instructor, as_learner):
    draft_id, [draft_lesson] = create_course(client, as_instructor, lessons=1, status="draft")
    archived_id, [archived_lesson] = create_course(client, as_instructor, lessons=1, status="archived")

    responses = [
        complete(client, as_learner, draft_id, draft_lesson),
        complete(client, as_learner, archived_id, archived_lesson),  # not enrolled, so it stays invisible
        complete(client, as_learner, 999999, draft_lesson),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert responses[0].json() == responses[1].json() == responses[2].json()


def test_a_lesson_from_another_course_or_a_missing_lesson_gives_404(client, as_instructor, as_learner):
    course_id, _ = enrolled_course(client, as_instructor, as_learner)
    _, [lesson_elsewhere, *_] = create_course(client, as_instructor)

    assert complete(client, as_learner, course_id, lesson_elsewhere).status_code == 404
    assert complete(client, as_learner, course_id, 999999).status_code == 404


# --- Locking and the database's own checks --------------------------------------------------------

COURSE_SHARE_LOCK = r"^\s*SELECT\b.*\bFROM courses\b.*\bFOR SHARE\b"
COURSE_READ = r"^\s*SELECT\b.*\bFROM courses\b"
ENROLLMENT_LOCK = r"^\s*SELECT\b.*\bFROM enrollments\b.*\bFOR UPDATE\b"
WRITE = r"^\s*(INSERT|UPDATE|DELETE)\b"


def test_completing_locks_the_course_then_the_enrolment_before_writing(
    client, as_instructor, as_learner, recorded_sql, first_index
):
    course_id, [first, *_] = enrolled_course(client, as_instructor, as_learner)

    with recorded_sql() as statements:
        response = complete(client, as_learner, course_id, first)

    assert response.status_code == 200
    course_lock = first_index(statements, COURSE_SHARE_LOCK)
    enrollment_lock = first_index(statements, ENROLLMENT_LOCK)
    assert course_lock is not None, "the course row was never locked"
    assert enrollment_lock is not None, "the enrolment row was never locked"
    assert first_index(statements, COURSE_READ) == course_lock  # the first read of the course is the locking one
    assert course_lock < enrollment_lock < first_index(statements, WRITE)


def test_the_database_keeps_one_completion_per_lesson_and_enrolment(client, db, learner, as_instructor, as_learner):
    course_id, [first, *_] = enrolled_course(client, as_instructor, as_learner)
    enrollment = enrollment_of(db, learner, course_id)
    db.add_all(LessonCompletion(enrollment_id=enrollment.id, lesson_id=first) for _ in range(2))

    with pytest.raises(IntegrityError, match="uq_lesson_completions_enrollment_id_lesson_id"):
        db.flush()


# --- Removing lessons -----------------------------------------------------------------------------


def test_a_lesson_a_learner_has_completed_cannot_be_removed(client, db, as_instructor, as_learner):
    course_id, [first, _second, _third] = enrolled_course(client, as_instructor, as_learner)
    complete(client, as_learner, course_id, first)
    log_rows_before = count_log_rows(db, course_id)

    response = client.delete(f"/courses/{course_id}/lessons/{first}", headers=as_instructor)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Learners have completed this lesson, so it can't be removed. You can still edit it."
    )
    db.expire_all()
    assert db.get(Lesson, first) is not None
    assert count_log_rows(db, course_id) == log_rows_before


def test_a_lesson_nobody_has_completed_can_still_be_removed(client, db, as_instructor, as_learner):
    course_id, [first, _second, third] = enrolled_course(client, as_instructor, as_learner)
    complete(client, as_learner, course_id, first)

    response = client.delete(f"/courses/{course_id}/lessons/{third}", headers=as_instructor)

    assert response.status_code == 204
    db.expire_all()
    assert db.get(Lesson, third) is None


def test_the_database_refuses_to_delete_a_completed_lesson(client, db, as_instructor, as_learner):
    course_id, [first, *_] = enrolled_course(client, as_instructor, as_learner)
    complete(client, as_learner, course_id, first)

    with pytest.raises(IntegrityError, match="fk_lesson_completions_lesson_id_lessons"):
        db.execute(delete(Lesson).where(Lesson.id == first))


def test_removing_a_lesson_completes_learners_who_had_done_every_other_lesson(
    client, db, make_user, auth_header, learner, as_instructor, as_learner
):
    course_id, [first, second, third] = enrolled_course(client, as_instructor, as_learner, lessons=3)
    sam = make_user(email="sam@example.com", role=Role.LEARNER)
    jo = make_user(email="jo@example.com", role=Role.LEARNER)
    as_sam, as_jo = auth_header(sam), auth_header(jo)
    client.post(f"/courses/{course_id}/enroll", headers=as_sam)
    client.post(f"/courses/{course_id}/enroll", headers=as_jo)
    # Alex has done lessons 1 and 2, Sam only lesson 1, and Jo hasn't started.
    complete(client, as_learner, course_id, first)
    complete(client, as_learner, course_id, second)
    complete(client, as_sam, course_id, first)
    alex_last_activity = enrollment_of(db, learner, course_id).last_activity_at

    response = client.delete(f"/courses/{course_id}/lessons/{third}", headers=as_instructor)

    assert response.status_code == 204
    alex = enrollment_of(db, learner, course_id)
    assert alex.status == EnrollmentStatus.COMPLETED
    assert alex.completed_at > alex_last_activity  # completed at the removal, after their last lesson
    assert alex.last_activity_at == alex_last_activity  # unchanged: Alex didn't do anything
    assert enrollment_of(db, sam, course_id).status == EnrollmentStatus.IN_PROGRESS  # lesson 2 still to do
    assert enrollment_of(db, jo, course_id).status == EnrollmentStatus.NOT_STARTED
