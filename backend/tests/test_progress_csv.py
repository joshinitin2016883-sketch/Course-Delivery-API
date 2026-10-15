"""Goal 7, the progress export: GET /courses/{id}/progress.csv gives the same learners, in the same order, as
GET /courses/{id}/progress, as a CSV file an instructor can open in a spreadsheet."""
import csv
import io
from datetime import datetime, timezone

import pytest

from app.core.config import CORS_ORIGINS
from app.models import Role
from app.services.export_service import COLUMNS

COURSE = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def as_priya(make_user, auth_header):
    return auth_header(make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah"))


def published_course(client, headers, lessons=2):
    course_id = client.post("/courses", json=COURSE, headers=headers).json()["id"]
    for number in range(1, lessons + 1):
        client.post(f"/courses/{course_id}/lessons", json={"title": f"Lesson {number}", "content": "Text"}, headers=headers)
    client.post(f"/courses/{course_id}/publish", headers=headers)
    return course_id


def enrolled_learner(client, make_user, auth_header, course_id, email, name):
    learner = make_user(email=email, role=Role.LEARNER, full_name=name)
    client.post(f"/courses/{course_id}/enroll", headers=auth_header(learner))
    return auth_header(learner)


def read_csv(response):
    """The rows of the CSV, decoded the way a reader should: utf-8-sig skips the byte-order mark."""
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_the_csv_has_the_same_learners_in_the_same_order_as_the_progress_list(client, make_user, auth_header, as_priya):
    course_id = published_course(client, as_priya)
    as_alex = enrolled_learner(client, make_user, auth_header, course_id, "alex@example.com", "Alex Chen")
    enrolled_learner(client, make_user, auth_header, course_id, "maria@example.com", "Maria Garcia")
    first_lesson = client.get(f"/courses/{course_id}", headers=as_priya).json()["lessons"][0]["id"]
    client.post(f"/courses/{course_id}/lessons/{first_lesson}/complete", headers=as_alex)

    response = client.get(f"/courses/{course_id}/progress.csv", headers=as_priya)
    progress = client.get(f"/courses/{course_id}/progress", headers=as_priya).json()

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    header, *rows = read_csv(response)
    assert header == COLUMNS
    assert [row[1] for row in rows] == [entry["learner"]["email"] for entry in progress]
    alex = next(row for row in rows if row[1] == "alex@example.com")
    assert alex[:5] == ["Alex Chen", "alex@example.com", "in_progress", "1", "2"]


def test_times_are_iso_8601_utc_to_the_second_and_empty_when_not_yet(client, make_user, auth_header, as_priya):
    course_id = published_course(client, as_priya)
    enrolled_learner(client, make_user, auth_header, course_id, "maria@example.com", "Maria Garcia")

    [maria] = read_csv(client.get(f"/courses/{course_id}/progress.csv", headers=as_priya))[1:]
    progress = client.get(f"/courses/{course_id}/progress", headers=as_priya).json()[0]

    enrolled_at = maria[COLUMNS.index("enrolled_at")]
    assert enrolled_at.endswith("Z") and len(enrolled_at) == len("2026-10-15T08:53:00Z")
    expected = datetime.fromisoformat(progress["enrolled_at"]).astimezone(timezone.utc).replace(microsecond=0)
    assert datetime.fromisoformat(enrolled_at.replace("Z", "+00:00")) == expected
    assert [maria[COLUMNS.index(column)] for column in ("started_at", "completed_at", "last_activity_at")] == ["", "", ""]


@pytest.mark.parametrize("name", ['=HYPERLINK("http://evil.example","Click me")', "+1 caller", "-minus", "@sum", "\tTab"])
def test_a_cell_a_spreadsheet_would_run_as_a_formula_starts_with_an_apostrophe(client, make_user, auth_header, as_priya, name):
    course_id = published_course(client, as_priya)
    enrolled_learner(client, make_user, auth_header, course_id, "evil@example.com", name)

    [row] = read_csv(client.get(f"/courses/{course_id}/progress.csv", headers=as_priya))[1:]

    assert row[0] == "'" + name


def test_ordinary_names_are_left_as_they_are(client, make_user, auth_header, as_priya):
    course_id = published_course(client, as_priya)
    enrolled_learner(client, make_user, auth_header, course_id, "alex@example.com", "Alex Chen")

    [row] = read_csv(client.get(f"/courses/{course_id}/progress.csv", headers=as_priya))[1:]

    assert row[0] == "Alex Chen"


def test_the_file_starts_with_the_utf8_byte_order_mark(client, as_priya):
    course_id = published_course(client, as_priya)

    response = client.get(f"/courses/{course_id}/progress.csv", headers=as_priya)

    assert response.content.startswith(b"\xef\xbb\xbf")


def test_a_non_ascii_name_reads_back_unchanged(client, make_user, auth_header, as_priya):
    course_id = published_course(client, as_priya)
    enrolled_learner(client, make_user, auth_header, course_id, "jose@example.com", "José Núñez")

    [row] = read_csv(client.get(f"/courses/{course_id}/progress.csv", headers=as_priya))[1:]

    assert row[0] == "José Núñez"


def test_the_file_is_an_attachment_named_after_the_course_and_the_utc_date(client, as_priya):
    course_id = published_course(client, as_priya)

    response = client.get(f"/courses/{course_id}/progress.csv", headers=as_priya)

    today = datetime.now(timezone.utc).date().isoformat()
    assert response.headers["content-disposition"] == f'attachment; filename="course-{course_id}-progress-{today}.csv"'


def test_learners_cannot_export(client, make_user, auth_header, as_priya):
    course_id = published_course(client, as_priya)
    as_alex = enrolled_learner(client, make_user, auth_header, course_id, "alex@example.com", "Alex Chen")

    response = client.get(f"/courses/{course_id}/progress.csv", headers=as_alex)

    assert (response.status_code, response.json()["detail"]) == (403, "Only instructors can do this.")


def test_draft_and_archived_courses_can_still_be_exported(client, make_user, auth_header, as_priya):
    draft_id = client.post("/courses", json=COURSE, headers=as_priya).json()["id"]
    archived_id = published_course(client, as_priya)
    enrolled_learner(client, make_user, auth_header, archived_id, "alex@example.com", "Alex Chen")
    client.post(f"/courses/{archived_id}/archive", headers=as_priya)

    draft = client.get(f"/courses/{draft_id}/progress.csv", headers=as_priya)
    archived = client.get(f"/courses/{archived_id}/progress.csv", headers=as_priya)

    assert draft.status_code == 200 and read_csv(draft) == [COLUMNS]
    assert archived.status_code == 200 and [row[1] for row in read_csv(archived)[1:]] == ["alex@example.com"]


def test_the_browser_may_read_the_filename_from_another_origin(client, as_priya):
    if not CORS_ORIGINS:
        pytest.skip("CORS_ORIGINS isn't set, so no origin may call the API")
    course_id = published_course(client, as_priya)

    response = client.get(f"/courses/{course_id}/progress.csv", headers={**as_priya, "Origin": CORS_ORIGINS[0]})

    assert "content-disposition" in response.headers["access-control-expose-headers"].lower()
