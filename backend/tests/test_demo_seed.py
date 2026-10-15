"""The demo data (python -m app.seed --demo): it shows every case the pages have, and it is exactly what the
services would have left behind, so the demo never shows something the app itself couldn't produce."""
from collections import Counter

import pytest
from sqlalchemy import func, select

from app import demo_seed
from app.models import Action, ActivityLog, AlertDismissal, Course, Enrollment, Lesson, LessonCompletion, User
from app.seed import create_demo_accounts
from app.services import alert_service, dashboard_service

PASSWORD_HASH = "not-a-real-hash"  # no one signs in here


@pytest.fixture
def seeded(db):
    create_demo_accounts(db, PASSWORD_HASH)
    assert demo_seed.add_demo_data(db, PASSWORD_HASH) is not None
    return db


@pytest.fixture
def priya(seeded):
    return seeded.scalar(select(User).where(User.email == "instructor@example.com"))


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_the_demo_data_shows_every_case(seeded, priya):
    db = seeded
    assert Counter(db.scalars(select(Course.status))) == {"published": 5, "draft": 1, "archived": 1}
    assert set(db.scalars(select(Enrollment.status))) == {"not_started", "in_progress", "completed"}
    numbers = dashboard_service.dashboard(db, priya)
    assert numbers.learners == 25  # the 5 demo learners and 20 more
    # Completions in most of the 8 weeks, so the chart has a shape.
    assert sum(week.completions > 0 for week in numbers.completions_by_week) >= 5
    # Four alerts show: the fifth quiet learner's was dismissed.
    alerts = alert_service.list_alerts(db, priya)
    assert sorted(alert.days_quiet for alert in alerts) == [16, 18, 21, 25]
    assert count(db, AlertDismissal) == 1
    assert db.scalar(select(func.count()).where(ActivityLog.action == Action.COMMENTED)) == 6  # a few comments


def test_every_enrolment_is_what_the_services_would_have_left(seeded):
    """In progress: some lessons done but not all, and the last activity is the latest completion.
    Completed: every lesson done, finished at the last one. Not started: nothing done and no times."""
    db = seeded
    now = db.scalar(select(func.now()))
    for enrollment in db.scalars(select(Enrollment)):
        lessons = db.scalar(select(func.count()).where(Lesson.course_id == enrollment.course_id))
        times = sorted(db.scalars(
            select(LessonCompletion.completed_at).where(LessonCompletion.enrollment_id == enrollment.id)
        ))
        what = (enrollment.course_id, enrollment.user_id, enrollment.status)
        if enrollment.status == "not_started":
            assert times == [] and enrollment.last_activity_at is None, what
        else:
            assert 0 < len(times) <= lessons, what
            assert (enrollment.started_at, enrollment.last_activity_at) == (times[0], times[-1]), what
            assert enrollment.enrolled_at <= times[0] and times[-1] <= now, what
        if enrollment.status == "in_progress":
            assert len(times) < lessons, what
        if enrollment.status == "completed":
            assert len(times) == lessons and enrollment.completed_at == times[-1], what


def test_the_activity_log_reads_in_time_order(seeded):
    db = seeded
    for course in db.scalars(select(Course)):
        entries = db.scalars(
            select(ActivityLog).where(ActivityLog.course_id == course.id).order_by(ActivityLog.id)
        ).all()
        assert entries[0].action == Action.CREATED, course.title
        assert [entry.created_at for entry in entries] == sorted(entry.created_at for entry in entries), course.title
        assert (Action.PUBLISHED in [entry.action for entry in entries]) == (course.status != "draft"), course.title


def test_demo_data_only_goes_into_a_database_with_no_courses(seeded):
    db = seeded
    before = (count(db, User), count(db, Course), count(db, Enrollment))

    assert demo_seed.add_demo_data(db, PASSWORD_HASH) is None
    assert (count(db, User), count(db, Course), count(db, Enrollment)) == before
