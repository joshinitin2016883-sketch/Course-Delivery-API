"""Goal 6, finding courses: GET /courses lists every course the viewer can see, with search, filters,
sorting and pages, all done in the database.

Courses are added straight to the database here, with fixed creation times, so the tests control the order.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Course, Enrollment, Role

BASE_TIME = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def priya(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def daniel(make_user):
    return make_user(email="daniel@example.com", role=Role.INSTRUCTOR, full_name="Daniel Okafor")


@pytest.fixture
def alex(make_user):
    return make_user(email="alex@example.com", role=Role.LEARNER, full_name="Alex Chen")


@pytest.fixture
def as_priya(priya, auth_header):
    return auth_header(priya)


@pytest.fixture
def as_alex(alex, auth_header):
    return auth_header(alex)


def add_course(db, instructor_id, title, *, description="A course.", category="skills", status="published", minutes=0):
    """Save a course directly, created `minutes` after BASE_TIME. Returns its id."""
    course = Course(
        title=title,
        description=description,
        category=category,
        status=status,
        instructor_id=instructor_id,
        created_at=BASE_TIME + timedelta(minutes=minutes),
    )
    db.add(course)
    db.commit()
    return course.id


def enrol(db, learner_id, course_id, **fields):
    db.add(Enrollment(course_id=course_id, user_id=learner_id, enrolled_by=learner_id, **fields))
    db.commit()


def list_courses(client, headers, **params):
    return client.get("/courses", headers=headers, params=params)


def titles(response):
    return [item["title"] for item in response.json()["items"]]


def ids(response):
    return [item["id"] for item in response.json()["items"]]


# --- Who sees what --------------------------------------------------------------------------------


def test_learners_see_published_courses_and_instructors_see_every_course(client, db, priya, as_priya, as_alex):
    add_course(db, priya.id, "Draft course", status="draft", minutes=1)
    add_course(db, priya.id, "Live course", status="published", minutes=2)
    add_course(db, priya.id, "Old course", status="archived", minutes=3)

    assert titles(list_courses(client, as_alex)) == ["Live course"]
    assert titles(list_courses(client, as_priya)) == ["Old course", "Live course", "Draft course"]


def test_no_parameter_shows_a_learner_a_draft_or_archived_course(client, db, priya, alex, as_alex):
    add_course(db, priya.id, "Secret draft", description="Hidden plans", status="draft", minutes=1)
    retired = add_course(db, priya.id, "Retired course", description="Hidden history", status="archived", minutes=2)
    enrol(db, alex.id, retired)  # even an archived course they're enrolled in stays out of this list
    add_course(db, priya.id, "Visible course", minutes=3)
    attempts = [
        {},
        {"status": "draft"},
        {"status": "archived"},
        {"q": "hidden"},
        {"q": "secret"},
        {"category": "skills"},
        {"instructor_id": priya.id},
        {"sort": "title", "order": "desc"},
        {"sort": "enrollment_count"},
        {"page_size": 100},
    ]

    for params in attempts:
        response = list_courses(client, as_alex, **params)
        assert response.status_code == 200, params
        assert set(titles(response)) <= {"Visible course"}, params
        assert response.json()["total"] == len(response.json()["items"]), params


def test_a_learner_filtering_by_draft_or_archived_gets_an_empty_page(client, db, priya, as_alex):
    add_course(db, priya.id, "Secret draft", status="draft")
    add_course(db, priya.id, "Retired course", status="archived")
    add_course(db, priya.id, "Visible course")

    for status in ("draft", "archived"):
        response = list_courses(client, as_alex, status=status)
        assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert titles(list_courses(client, as_alex, status="published")) == ["Visible course"]


# --- Search and filters ---------------------------------------------------------------------------


def test_search_matches_the_title_or_the_description_ignoring_case(client, db, priya, as_priya):
    add_course(db, priya.id, "Fire safety", description="Alarms and exits", minutes=1)
    add_course(db, priya.id, "Data protection", description="Handling personal data", minutes=2)
    add_course(db, priya.id, "First aid", description="Treating a burn from a FIRE", minutes=3)

    assert titles(list_courses(client, as_priya, q="fire")) == ["First aid", "Fire safety"]
    assert titles(list_courses(client, as_priya, q="ALARM")) == ["Fire safety"]


def test_percent_underscore_and_backslash_in_the_search_are_plain_characters(client, db, priya, as_priya):
    add_course(db, priya.id, "100% attendance", minutes=1)
    add_course(db, priya.id, "1000 attendance", minutes=2)  # '100%' as a wildcard would match this too
    add_course(db, priya.id, "snake_case names", minutes=3)
    add_course(db, priya.id, "snakeXcase names", minutes=4)  # '_' as a wildcard would match this too
    add_course(db, priya.id, "C:\\temp folders", minutes=5)
    add_course(db, priya.id, "C:temp folders", minutes=6)  # an unescaped backslash would match this too

    assert titles(list_courses(client, as_priya, q="100%")) == ["100% attendance"]
    assert titles(list_courses(client, as_priya, q="snake_case")) == ["snake_case names"]
    assert titles(list_courses(client, as_priya, q="C:\\temp")) == ["C:\\temp folders"]


def test_each_filter_on_its_own_and_all_of_them_together(client, db, priya, daniel, as_priya):
    add_course(db, priya.id, "Fire safety", category="compliance", minutes=1)
    add_course(db, priya.id, "Fire wardens", category="compliance", status="draft", minutes=2)
    add_course(db, daniel.id, "Fire drills", category="compliance", minutes=3)
    add_course(db, priya.id, "Welcome week", category="onboarding", minutes=4)

    assert titles(list_courses(client, as_priya, category="compliance")) == ["Fire drills", "Fire wardens", "Fire safety"]
    assert titles(list_courses(client, as_priya, status="draft")) == ["Fire wardens"]
    assert titles(list_courses(client, as_priya, instructor_id=daniel.id)) == ["Fire drills"]
    everything = {"q": "fire", "category": "compliance", "status": "published", "instructor_id": priya.id}
    assert titles(list_courses(client, as_priya, **everything)) == ["Fire safety"]


def test_an_unknown_instructor_gives_an_empty_page_and_a_blank_search_is_no_search(client, db, priya, as_priya):
    add_course(db, priya.id, "Fire safety", minutes=1)
    add_course(db, priya.id, "First aid", minutes=2)

    assert list_courses(client, as_priya, instructor_id=999999).json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }
    assert titles(list_courses(client, as_priya, q="   ")) == ["First aid", "Fire safety"]


# --- Sorting --------------------------------------------------------------------------------------


def test_title_sort_ignores_case_and_breaks_ties_by_id(client, db, priya, as_priya):
    apple = add_course(db, priya.id, "apple", minutes=1)
    banana_capital = add_course(db, priya.id, "Banana", minutes=2)
    banana_small = add_course(db, priya.id, "banana", minutes=3)
    cherry = add_course(db, priya.id, "Cherry", minutes=4)

    ascending = list_courses(client, as_priya, sort="title", order="asc")
    descending = list_courses(client, as_priya, sort="title", order="desc")

    assert ids(ascending) == [apple, banana_capital, banana_small, cherry]
    assert ids(descending) == [cherry, banana_small, banana_capital, apple]


def test_titles_that_differ_only_in_spaces_or_punctuation_sort_the_same_on_every_database(
    client, db, priya, as_priya, recorded_sql
):
    # Byte order after lower(): space < "-" < "_" < letters. A linguistic collation (such as en_US on glibc,
    # or ICU) skips spaces and punctuation at first, and could put these four in another order.
    no_gap = add_course(db, priya.id, "Firstaid", minutes=1)
    underscore = add_course(db, priya.id, "First_aid", minutes=2)
    space = add_course(db, priya.id, "First aid", minutes=3)
    hyphen = add_course(db, priya.id, "First-aid", minutes=4)

    with recorded_sql() as statements:
        ascending = list_courses(client, as_priya, sort="title", order="asc")
    descending = list_courses(client, as_priya, sort="title", order="desc")

    assert ids(ascending) == [space, hyphen, underscore, no_gap]
    assert ids(descending) == [no_gap, underscore, hyphen, space]
    # The local test database (Alpine) already sorts by bytes, so the order alone couldn't catch a missing
    # COLLATE "C" here: the query itself has to ask for it.
    assert any('lower(courses.title) COLLATE "C"' in statement for statement in statements)


def test_creation_date_sort_breaks_ties_by_id(client, db, priya, as_priya):
    first = add_course(db, priya.id, "First", minutes=1)
    tie_a = add_course(db, priya.id, "Tie A", minutes=2)
    tie_b = add_course(db, priya.id, "Tie B", minutes=2)
    last = add_course(db, priya.id, "Last", minutes=3)

    assert ids(list_courses(client, as_priya, sort="created_at", order="asc")) == [first, tie_a, tie_b, last]
    assert ids(list_courses(client, as_priya, sort="created_at", order="desc")) == [last, tie_b, tie_a, first]


def test_enrolment_count_sort_breaks_ties_by_id(client, db, make_user, priya, as_priya):
    learners = [make_user(email=f"learner{n}@example.com", role=Role.LEARNER).id for n in range(2)]
    nobody = add_course(db, priya.id, "Nobody", minutes=1)
    one_a = add_course(db, priya.id, "One A", minutes=2)
    one_b = add_course(db, priya.id, "One B", minutes=3)
    two = add_course(db, priya.id, "Two", minutes=4)
    enrol(db, learners[0], one_a)
    enrol(db, learners[0], one_b)
    enrol(db, learners[0], two)
    enrol(db, learners[1], two)

    ascending = list_courses(client, as_priya, sort="enrollment_count", order="asc")
    descending = list_courses(client, as_priya, sort="enrollment_count", order="desc")

    assert ids(ascending) == [nobody, one_a, one_b, two]
    assert ids(descending) == [two, one_b, one_a, nobody]
    assert [item["enrollment_count"] for item in descending.json()["items"]] == [2, 1, 1, 0]


def test_newest_first_by_default_and_each_sort_has_its_own_default_order(client, db, priya, alex, as_priya):
    older = add_course(db, priya.id, "B older", minutes=1)
    newer = add_course(db, priya.id, "A newer", minutes=2)
    enrol(db, alex.id, older)

    assert ids(list_courses(client, as_priya)) == [newer, older]  # created_at, newest first
    assert ids(list_courses(client, as_priya, sort="title")) == [newer, older]  # A to Z
    assert ids(list_courses(client, as_priya, sort="enrollment_count")) == [older, newer]  # most enrolled first


# --- Pages ----------------------------------------------------------------------------------------


def test_pages_split_the_list_without_repeats_or_gaps_and_report_the_total(client, db, priya, as_priya):
    courses = [add_course(db, priya.id, f"Course {n}", minutes=n) for n in range(1, 6)]

    pages = [
        list_courses(client, as_priya, sort="created_at", order="asc", page=page, page_size=2).json()
        for page in (1, 2, 3, 4)
    ]

    assert [len(page["items"]) for page in pages] == [2, 2, 1, 0]
    assert [page["total"] for page in pages] == [5, 5, 5, 5]
    assert [item["id"] for page in pages for item in page["items"]] == courses
    assert pages[3] == {"items": [], "total": 5, "page": 4, "page_size": 2}  # past the end: empty, with the total


@pytest.mark.parametrize(
    "params",
    [
        {"sort": "popularity"},
        {"order": "sideways"},
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
        {"category": "cooking"},
        {"status": "deleted"},
        {"q": "x" * 101},
        {"instructor_id": "abc"},
    ],
    ids=[
        "unknown sort",
        "unknown order",
        "page 0",
        "page size 0",
        "page size over 100",
        "unknown category",
        "unknown status",
        "search too long",
        "instructor id not a number",
    ],
)
def test_bad_parameters_give_422(client, as_priya, params):
    response = list_courses(client, as_priya, **params)

    assert response.status_code == 422


# --- What each row carries ------------------------------------------------------------------------


def test_each_row_has_what_a_list_needs(client, db, priya, alex, as_priya):
    course_id = add_course(db, priya.id, "Fire safety", description="Alarms", category="compliance", minutes=1)
    enrol(db, alex.id, course_id)

    [item] = list_courses(client, as_priya).json()["items"]

    assert datetime.fromisoformat(item.pop("created_at")) == BASE_TIME + timedelta(minutes=1)
    assert item == {
        "id": course_id,
        "title": "Fire safety",
        "description": "Alarms",
        "category": "compliance",
        "status": "published",
        "instructor": {"id": priya.id, "full_name": "Priya Shah"},
        "enrollment_count": 1,
        "enrolled": False,
    }


def test_the_enrolment_count_includes_every_state(client, db, make_user, priya, as_priya):
    course_id = add_course(db, priya.id, "Fire safety")
    now = datetime.now(timezone.utc)
    states = [
        {},
        {"status": "in_progress", "started_at": now, "last_activity_at": now},
        {"status": "completed", "started_at": now, "completed_at": now, "last_activity_at": now},
    ]
    for number, fields in enumerate(states):
        enrol(db, make_user(email=f"learner{number}@example.com", role=Role.LEARNER).id, course_id, **fields)

    [item] = list_courses(client, as_priya).json()["items"]

    assert item["enrollment_count"] == 3


def test_enrolled_is_true_only_for_the_viewers_own_enrolments(client, db, make_user, auth_header, priya, alex, as_priya):
    sam = make_user(email="sam@example.com", role=Role.LEARNER)
    fire_safety = add_course(db, priya.id, "Fire safety", minutes=1)
    data_protection = add_course(db, priya.id, "Data protection", minutes=2)
    enrol(db, alex.id, fire_safety)
    enrol(db, sam.id, data_protection)

    def enrolled_flags(headers):
        return {item["title"]: item["enrolled"] for item in list_courses(client, headers).json()["items"]}

    assert enrolled_flags(auth_header(alex)) == {"Fire safety": True, "Data protection": False}
    assert enrolled_flags(auth_header(sam)) == {"Fire safety": False, "Data protection": True}
    assert enrolled_flags(as_priya) == {"Fire safety": False, "Data protection": False}


# --- Everything in one query, plus the total ------------------------------------------------------


def test_a_page_takes_the_same_number_of_queries_however_many_courses(
    client, db, make_user, alex, as_alex, recorded_sql
):
    learner_id = alex.id

    def queries_after_adding(numbers):
        for number in numbers:
            # Each course gets its own instructor, so loading instructors one at a time would show up here.
            instructor_id = make_user(email=f"instructor{number}@example.com", role=Role.INSTRUCTOR).id
            enrol(db, learner_id, add_course(db, instructor_id, f"Course {number}"))
        db.expunge_all()  # empty the session's cache, so everything has to come from the database
        with recorded_sql() as statements:
            response = list_courses(client, as_alex, page_size=100)
        assert response.status_code == 200
        return len(statements)

    assert queries_after_adding(range(1, 2)) == queries_after_adding(range(2, 32))  # 1 course, then 31
