"""Goal 8, the dashboard: GET /dashboard gives instructors the headline numbers, enrolments by course and state,
and course completions per week for the last eight weeks.

The dashboard measures time from the database's now(). Inside a test that is the start of the test's
transaction, so it doesn't move: the rows here are placed relative to it, with no clock mocking.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from app.models import Course, Enrollment, Role

# Zones with daylight saving, north and south of the equator, for the time zone test below.
DST_ZONES = ["America/New_York", "Europe/London", "Australia/Sydney", "Pacific/Auckland", "America/Santiago"]
CLOCK_CHANGES_IN_LAST_8_WEEKS = text("""
    SELECT (now() AT TIME ZONE :zone) - (now() AT TIME ZONE 'UTC')
        <> ((now() - interval '8 weeks') AT TIME ZONE :zone) - ((now() - interval '8 weeks') AT TIME ZONE 'UTC')
""")


@pytest.fixture
def priya(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def as_priya(priya, auth_header):
    return auth_header(priya)


@pytest.fixture
def now(db):
    """The database's now(), in UTC: the clock the dashboard uses."""
    return db.scalar(select(func.now())).astimezone(timezone.utc)


def add_course(db, instructor, title, status="published"):
    course = Course(title=title, description="A course.", category="skills", status=status, instructor_id=instructor.id)
    db.add(course)
    db.commit()
    return course


def add_enrollment(db, course, learner, status="not_started", at=None):
    """An enrolment in the given state. `at` is the latest activity, and the completion time for a completed one."""
    times = {}
    if status != "not_started":
        times = {"started_at": at - timedelta(days=1), "last_activity_at": at}
    if status == "completed":
        times["completed_at"] = at
    db.add(Enrollment(course_id=course.id, user_id=learner.id, enrolled_by=learner.id, status=status, **times))
    db.commit()


def learners(make_user, *names):
    return [make_user(email=f"{name.lower()}@example.com", role=Role.LEARNER, full_name=name) for name in names]


def get_dashboard(client, headers):
    return client.get("/dashboard", headers=headers).json()


def test_the_headline_numbers(client, db, make_user, priya, as_priya, now):
    alex, maria, sam = learners(make_user, "Alex", "Maria", "Sam")
    fire, data = add_course(db, priya, "Fire safety"), add_course(db, priya, "Data protection")
    add_course(db, priya, "Draft course", status="draft")
    old = add_course(db, priya, "Old policy", status="archived")
    add_enrollment(db, fire, alex, "in_progress", now - timedelta(days=1))
    add_enrollment(db, data, alex, "in_progress", now - timedelta(days=2))  # Alex counts once
    add_enrollment(db, old, maria, "in_progress", now - timedelta(days=3))  # frozen in an archived course
    add_enrollment(db, fire, sam, "completed", now)

    numbers = get_dashboard(client, as_priya)

    assert numbers["learners"] == 3  # every learner account; Priya is an instructor
    assert numbers["published_courses"] == 2
    assert numbers["completions_this_month"] == 1
    assert numbers["learners_in_progress"] == 1


def test_completions_this_month_start_at_midnight_utc_on_the_first(client, db, make_user, priya, as_priya, now):
    alex, maria = learners(make_user, "Alex", "Maria")
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fire, data = add_course(db, priya, "Fire safety"), add_course(db, priya, "Data protection")
    add_enrollment(db, fire, alex, "completed", month_start)
    add_enrollment(db, data, maria, "completed", month_start - timedelta(seconds=1))

    assert get_dashboard(client, as_priya)["completions_this_month"] == 1


def test_enrolments_by_course_and_state(client, db, make_user, priya, as_priya, now):
    alex, maria, sam = learners(make_user, "Alex", "Maria", "Sam")
    fire, data = add_course(db, priya, "Fire safety"), add_course(db, priya, "data protection")
    add_course(db, priya, "Nobody enrolled")
    old = add_course(db, priya, "Old policy", status="archived")
    add_enrollment(db, fire, alex)
    add_enrollment(db, fire, maria, "in_progress", now)
    add_enrollment(db, fire, sam, "completed", now)
    add_enrollment(db, data, alex, "completed", now)
    add_enrollment(db, old, maria)

    rows = get_dashboard(client, as_priya)["by_course"]

    assert [(r["title"], r["status"], r["not_started"], r["in_progress"], r["completed"]) for r in rows] == [
        ("data protection", "published", 0, 0, 1),
        ("Fire safety", "published", 1, 1, 1),
        ("Old policy", "archived", 1, 0, 0),
    ]


def test_eight_weeks_of_completions_oldest_first_with_empty_weeks(client, db, make_user, priya, as_priya, now):
    people = learners(make_user, "Alex", "Maria", "Sam", "Jordan", "Fatima")
    this_monday = datetime.combine(now.date() - timedelta(days=now.weekday()), datetime.min.time(), timezone.utc)
    oldest_monday = this_monday - timedelta(weeks=7)
    course = add_course(db, priya, "Fire safety")
    for person, finished in zip(people, [
        now,  # this week
        this_monday - timedelta(weeks=3) + timedelta(hours=1),  # three weeks ago
        this_monday - timedelta(weeks=3) + timedelta(days=2),  # the same week
        oldest_monday,  # the very start of the oldest week shown
        oldest_monday - timedelta(seconds=1),  # just before it: not shown
    ]):
        add_enrollment(db, course, person, "completed", finished)

    weeks = get_dashboard(client, as_priya)["completions_by_week"]

    assert [week["week_start"] for week in weeks] == [str(oldest_monday.date() + timedelta(weeks=n)) for n in range(8)]
    assert all(date.fromisoformat(week["week_start"]).weekday() == 0 for week in weeks)  # Mondays
    assert [week["completions"] for week in weeks] == [1, 0, 0, 0, 2, 0, 0, 1]
    assert [week["partial"] for week in weeks] == [False] * 7 + [True]


def test_the_weeks_stay_on_utc_mondays_whatever_the_session_time_zone(client, db, make_user, priya, as_priya, now):
    # Only a daylight-saving change inside the 8 weeks could push a week start off midnight UTC, and no single
    # zone changes its clock in every 8 weeks of the year. So the test uses the first of these zones whose clock
    # changes inside the window, and skips when none does, so it never passes without crossing a change.
    zone = None
    for candidate in DST_ZONES:
        if db.scalar(CLOCK_CHANGES_IN_LAST_8_WEEKS, {"zone": candidate}):
            zone = candidate
            break
    if zone is None:
        pytest.skip("None of the daylight-saving zones changes its clock inside the current 8-week window.")
    db.execute(text(f"SET LOCAL TIME ZONE '{zone}'"))  # until the test's transaction ends
    this_monday = datetime.combine(now.date() - timedelta(days=now.weekday()), datetime.min.time(), timezone.utc)
    mondays = [this_monday - timedelta(weeks=7 - n) for n in range(8)]
    course = add_course(db, priya, "Fire safety")
    # One completion at the very first instant of each week, in UTC: a week start that drifted would miss it.
    for person, monday in zip(learners(make_user, *[f"Learner{n}" for n in range(8)]), mondays):
        add_enrollment(db, course, person, "completed", monday)

    weeks = get_dashboard(client, as_priya)["completions_by_week"]

    assert [week["week_start"] for week in weeks] == [str(monday.date()) for monday in mondays], zone
    assert [week["completions"] for week in weeks] == [1] * 8, zone


def test_learners_cannot_see_the_dashboard(client, make_user, auth_header):
    [alex] = learners(make_user, "Alex")

    response = client.get("/dashboard", headers=auth_header(alex))

    assert (response.status_code, response.json()["detail"]) == (403, "Only instructors can do this.")
