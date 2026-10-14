"""GET /instructors: the names the course list's instructor filter offers. Any signed-in user may ask for it."""
import pytest

from app.models import Role


@pytest.fixture
def priya(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def daniel(make_user):
    return make_user(email="daniel@example.com", role=Role.INSTRUCTOR, full_name="Daniel Okafor")


@pytest.fixture
def alex(make_user):
    return make_user(email="alex@example.com", role=Role.LEARNER, full_name="Alex Chen")


def test_learners_and_instructors_both_get_every_instructor_and_no_learners(client, auth_header, priya, daniel, alex):
    for viewer in (alex, priya):
        response = client.get("/instructors", headers=auth_header(viewer))

        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [daniel.id, priya.id]


def test_the_list_has_ids_and_names_only_and_never_an_email(client, auth_header, priya, daniel, alex):
    response = client.get("/instructors", headers=auth_header(alex))

    assert response.json() == [
        {"id": daniel.id, "full_name": "Daniel Okafor"},
        {"id": priya.id, "full_name": "Priya Shah"},
    ]
    assert "@" not in response.text


def test_the_list_needs_a_signed_in_user(client, priya):
    response = client.get("/instructors")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_instructors_are_sorted_by_name_ignoring_case_then_by_id(client, make_user, auth_header):
    # Saved out of order, with a lower-case name and two people of the same name.
    carl = make_user(email="carl@example.com", role=Role.INSTRUCTOR, full_name="Carl Ode")
    first_adam = make_user(email="adam1@example.com", role=Role.INSTRUCTOR, full_name="Adam Price")
    bea = make_user(email="bea@example.com", role=Role.INSTRUCTOR, full_name="bea Lane")
    second_adam = make_user(email="adam2@example.com", role=Role.INSTRUCTOR, full_name="Adam Price")

    response = client.get("/instructors", headers=auth_header(carl))

    # Byte order would put "bea" after "Carl"; lower() makes case not matter.
    assert [item["id"] for item in response.json()] == [first_adam.id, second_adam.id, bea.id, carl.id]
