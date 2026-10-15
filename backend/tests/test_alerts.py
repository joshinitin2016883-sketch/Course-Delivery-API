"""Goal 10, inactivity alerts: GET /alerts lists learners in progress on a published course who haven't completed
a lesson for more than 14 days, and POST /alerts/dismiss hides one until the learner is active again.

The rule uses the database's now(). Inside a test that is the start of the test's transaction, so it doesn't
move: last activity times are placed relative to it, with no clock mocking.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import AlertDismissal, Course, Enrollment, Lesson, Role


@pytest.fixture
def priya(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def as_priya(priya, auth_header):
    return auth_header(priya)


@pytest.fixture
def now(db):
    """The database's now(), in UTC: the clock the alerts use."""
    return db.scalar(select(func.now())).astimezone(timezone.utc)


def add_course(db, instructor, title="Fire safety", status="published"):
    """A course with two lessons, so completing one leaves a learner in progress."""
    course = Course(title=title, description="A course.", category="skills", status=status, instructor_id=instructor.id)
    db.add(course)
    db.flush()
    db.add_all([Lesson(course_id=course.id, title=f"Lesson {n}", content="Text", position=n) for n in (1, 2)])
    db.commit()
    return course


def add_learner(db, make_user, now, course, name, status="in_progress", quiet_for=timedelta(days=30)):
    """A learner who enrolled 60 days ago. Unless not started, they last completed a lesson `quiet_for` ago."""
    learner = make_user(email=f"{name.lower()}@example.com", role=Role.LEARNER, full_name=name)
    last_active = now - quiet_for
    times = {"enrolled_at": now - timedelta(days=60)}
    if status != "not_started":
        times |= {"started_at": last_active, "last_activity_at": last_active}
    if status == "completed":
        times["completed_at"] = last_active
    db.add(Enrollment(course_id=course.id, user_id=learner.id, enrolled_by=learner.id, status=status, **times))
    db.commit()
    return learner


def get_alerts(client, headers):
    return client.get("/alerts", headers=headers).json()


def names_and_days(alerts):
    return [(alert["learner"]["full_name"], alert["days_quiet"]) for alert in alerts]


def dismiss(client, headers, course, learner):
    return client.post("/alerts/dismiss", json={"course_id": course.id, "learner_id": learner.id}, headers=headers)


def test_more_than_14_days_quiet_is_an_alert_longest_quiet_first(client, db, make_user, priya, as_priya, now):
    course = add_course(db, priya)
    add_learner(db, make_user, now, course, "Alex", quiet_for=timedelta(days=14))  # exactly 14: not yet
    add_learner(db, make_user, now, course, "Sam", quiet_for=timedelta(days=14, minutes=1))
    jordan = add_learner(db, make_user, now, course, "Jordan", quiet_for=timedelta(days=30))

    alerts = get_alerts(client, as_priya)

    assert names_and_days(alerts) == [("Jordan", 30), ("Sam", 14)]
    assert alerts[0]["learner"] == {"id": jordan.id, "full_name": "Jordan", "email": "jordan@example.com"}
    assert alerts[0]["course"] == {"id": course.id, "title": "Fire safety"}
    assert datetime.fromisoformat(alerts[0]["last_activity_at"]) == now - timedelta(days=30)


def test_only_learners_in_progress_on_a_published_course_get_alerts(client, db, make_user, priya, as_priya, now):
    course = add_course(db, priya)
    old = add_course(db, priya, "Old policy", status="archived")
    add_learner(db, make_user, now, old, "Alex")  # progress in an archived course is frozen
    add_learner(db, make_user, now, course, "Maria", "completed")
    add_learner(db, make_user, now, course, "Sam", "not_started")

    assert get_alerts(client, as_priya) == []


def test_a_dismissed_alert_comes_back_when_the_learner_goes_quiet_again(
    client, db, make_user, auth_header, priya, as_priya, now
):
    course = add_course(db, priya)
    alex = add_learner(db, make_user, now, course, "Alex", quiet_for=timedelta(days=20))
    omar = make_user(email="omar@example.com", role=Role.INSTRUCTOR, full_name="Omar Haddad")

    assert dismiss(client, as_priya, course, alex).status_code == 204
    assert get_alerts(client, as_priya) == []
    assert get_alerts(client, auth_header(omar)) == []  # dismissed for every instructor (Decision 3)
    assert db.scalars(select(AlertDismissal.dismissed_by)).all() == [priya.id]

    # Alex completes a lesson, so is active again: still no alert...
    lesson = db.scalars(select(Lesson).where(Lesson.course_id == course.id)).first()
    completed = client.post(f"/courses/{course.id}/lessons/{lesson.id}/complete", headers=auth_header(alex))
    assert completed.status_code == 200
    assert get_alerts(client, as_priya) == []
    # ...then goes quiet for 15 days. The dismissal was for the earlier quiet spell, so the alert is back.
    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == alex.id))
    enrollment.last_activity_at = now - timedelta(days=15)
    db.commit()

    assert names_and_days(get_alerts(client, as_priya)) == [("Alex", 15)]


def test_dismissing_when_there_is_no_alert_is_a_conflict(client, db, make_user, priya, as_priya, now):
    course = add_course(db, priya)
    alex = add_learner(db, make_user, now, course, "Alex", quiet_for=timedelta(days=20))
    maria = add_learner(db, make_user, now, course, "Maria", quiet_for=timedelta(days=3))
    dismiss(client, as_priya, course, alex)

    again = dismiss(client, as_priya, course, alex)
    active = dismiss(client, as_priya, course, maria)

    assert (again.status_code, again.json()["detail"]) == (409, "This alert has already been dismissed.")
    assert (active.status_code, active.json()["detail"]) == (409, "This learner has no alert on this course any more.")
    assert db.scalar(select(func.count()).select_from(AlertDismissal)) == 1


def test_learners_cannot_see_or_dismiss_alerts(client, db, make_user, auth_header, priya, now):
    course = add_course(db, priya)
    alex = add_learner(db, make_user, now, course, "Alex")
    as_alex = auth_header(alex)

    for response in (client.get("/alerts", headers=as_alex), dismiss(client, as_alex, course, alex)):
        assert (response.status_code, response.json()["detail"]) == (403, "Only instructors can do this.")
