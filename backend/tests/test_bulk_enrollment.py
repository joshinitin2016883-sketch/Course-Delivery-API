"""Goal 7, bulk enrolment: an instructor pastes or uploads a list of email addresses, and the result reports
what happened to each one."""
import pytest
from sqlalchemy import select

from app.models import Enrollment, Role

COURSE = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


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
def maria(make_user):
    return make_user(email="maria@example.com", role=Role.LEARNER, full_name="Maria Garcia")


@pytest.fixture
def as_priya(priya, auth_header):
    return auth_header(priya)


def create_course(client, headers, status="published"):
    """A course with one lesson, moved to that status through the API. Returns its id."""
    course_id = client.post("/courses", json=COURSE, headers=headers).json()["id"]
    client.post(f"/courses/{course_id}/lessons", json={"title": "Lesson 1", "content": "Text"}, headers=headers)
    if status in ("published", "archived"):
        client.post(f"/courses/{course_id}/publish", headers=headers)
    if status == "archived":
        client.post(f"/courses/{course_id}/archive", headers=headers)
    return course_id


def bulk(client, headers, course_id, text):
    return client.post(f"/courses/{course_id}/enrollments/bulk", json={"text": text}, headers=headers)


def enrollments(db, course_id):
    return db.scalars(select(Enrollment).where(Enrollment.course_id == course_id)).all()


def test_every_outcome_in_one_request_in_the_order_pasted(client, db, auth_header, priya, daniel, alex, maria, as_priya):
    course_id = create_course(client, as_priya)
    client.post(f"/courses/{course_id}/enroll", headers=auth_header(alex))  # Alex enrolled himself earlier
    text = "  MARIA@example.com ,alex@example.com;\nnobody@example.com  not-an-email\n daniel@example.com maria@example.com Maria@Example.COM"

    response = bulk(client, as_priya, course_id, text)

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"email": "maria@example.com", "outcome": "enrolled"},
            {"email": "alex@example.com", "outcome": "already_enrolled"},
            {"email": "nobody@example.com", "outcome": "unknown"},
            {"email": "not-an-email", "outcome": "invalid"},
            {"email": "daniel@example.com", "outcome": "not_a_learner"},
        ],
        "counts": {"enrolled": 1, "already_enrolled": 1, "unknown": 1, "invalid": 1, "not_a_learner": 1},
        "repeats_removed": 2,
    }


def test_the_new_enrolment_records_the_instructor_and_the_learner_sees_the_course(client, db, auth_header, priya, maria, as_priya):
    course_id = create_course(client, as_priya)

    bulk(client, as_priya, course_id, "maria@example.com")

    [enrollment] = enrollments(db, course_id)
    assert (enrollment.user_id, enrollment.enrolled_by, enrollment.status) == (maria.id, priya.id, "not_started")
    my_courses = client.get("/me/courses", headers=auth_header(maria)).json()
    assert [entry["course"]["id"] for entry in my_courses] == [course_id]


def test_sending_the_same_list_again_reports_everyone_as_already_enrolled(client, db, alex, maria, as_priya):
    course_id = create_course(client, as_priya)
    bulk(client, as_priya, course_id, "alex@example.com maria@example.com")

    again = bulk(client, as_priya, course_id, "alex@example.com maria@example.com")

    assert again.json()["counts"] == {"enrolled": 0, "already_enrolled": 2, "unknown": 0, "invalid": 0, "not_a_learner": 0}
    assert len(enrollments(db, course_id)) == 2


@pytest.mark.parametrize("status", ["draft", "archived"])
def test_only_a_published_course_takes_learners(client, db, alex, as_priya, status):
    course_id = create_course(client, as_priya, status=status)

    response = bulk(client, as_priya, course_id, "alex@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == f"Only a published course can take new learners, and this course is {status}."
    assert enrollments(db, course_id) == []


def test_learners_cannot_bulk_enrol_even_into_a_course_that_does_not_exist(client, db, auth_header, alex, maria, as_priya):
    course_id = create_course(client, as_priya)

    response = bulk(client, auth_header(alex), course_id, "maria@example.com")
    missing = bulk(client, auth_header(alex), 999_999, "maria@example.com")

    assert (response.status_code, response.json()["detail"]) == (403, "Only instructors can do this.")
    assert missing.status_code == 403  # the role is checked before the lookup
    assert enrollments(db, course_id) == []


def test_an_unknown_course_is_404(client, as_priya):
    assert bulk(client, as_priya, 999_999, "alex@example.com").status_code == 404


@pytest.mark.parametrize("text", ["", "  ,;\n\t "])
def test_a_list_with_no_addresses_is_422(client, as_priya, text):
    course_id = create_course(client, as_priya)

    response = bulk(client, as_priya, course_id, text)

    assert (response.status_code, response.json()["detail"]) == (422, "Paste at least one email address.")


def test_500_distinct_addresses_are_accepted_and_501_are_refused(client, as_priya):
    course_id = create_course(client, as_priya)
    addresses = [f"person{n}@example.com" for n in range(501)]

    at_limit = bulk(client, as_priya, course_id, "\n".join(addresses[:500]))
    over_limit = bulk(client, as_priya, course_id, "\n".join(addresses))

    assert at_limit.status_code == 200 and at_limit.json()["counts"]["unknown"] == 500
    assert (over_limit.status_code, over_limit.json()["detail"]) == (422, "At most 500 addresses at a time; this list has 501.")


def test_repeats_do_not_count_towards_the_limit(client, as_priya):
    course_id = create_course(client, as_priya)

    response = bulk(client, as_priya, course_id, "\n".join(["same@example.com"] * 600))

    assert response.status_code == 200
    assert response.json()["repeats_removed"] == 599


def test_a_text_over_200000_characters_is_422(client, as_priya):
    course_id = create_course(client, as_priya)

    response = bulk(client, as_priya, course_id, "x" * 200_001)

    assert response.status_code == 422


def test_bulk_enrolment_takes_the_same_shared_lock_as_self_enrolment(client, maria, as_priya, recorded_sql, first_index):
    course_id = create_course(client, as_priya)

    with recorded_sql() as statements:
        bulk(client, as_priya, course_id, "maria@example.com")

    lock = first_index(statements, r"FROM courses .*FOR SHARE")
    insert = first_index(statements, r"INSERT INTO enrollments")
    assert lock is not None and insert is not None and lock < insert
    assert "ON CONFLICT ON CONSTRAINT uq_enrollments_course_id_user_id DO NOTHING" in statements[insert]
