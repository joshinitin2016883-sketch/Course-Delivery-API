"""Goal 9, history you cannot rewrite.

Every change to a course adds a log row naming who made it, and the database refuses to change or
delete log rows afterwards, no matter who asks. Comments are log rows too. The activity feed shows the
log newest first: every entry to instructors, only the comments to learners. A learner has to be enrolled
to comment or read the feed.
"""
import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import Action, ActivityLog, Role

FIRE_SAFETY = {"title": "Fire safety", "description": "What to do when the alarm goes off.", "category": "compliance"}


@pytest.fixture
def instructor(make_user):
    return make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")


@pytest.fixture
def learner(make_user):
    return make_user(email="alex@example.com", role=Role.LEARNER, full_name="Alex Chen")


@pytest.fixture
def course_id(client, instructor, auth_header):
    """A draft course, created through the API."""
    return client.post("/courses", json=FIRE_SAFETY, headers=auth_header(instructor)).json()["id"]


def publish_new_course(client, headers):
    """Create a course with one lesson and publish it, through the API. Returns the course id."""
    course_id = client.post("/courses", json=FIRE_SAFETY, headers=headers).json()["id"]
    client.post(f"/courses/{course_id}/lessons", json={"title": "Alarms", "content": "Text"}, headers=headers)
    client.post(f"/courses/{course_id}/publish", headers=headers)
    return course_id


def archive_new_course(client, headers):
    course_id = publish_new_course(client, headers)
    client.post(f"/courses/{course_id}/archive", headers=headers)
    return course_id


def enroll(client, headers, course_id):
    response = client.post(f"/courses/{course_id}/enroll", headers=headers)
    assert response.status_code == 201


def comment(client, headers, course_id, comment_text):
    return client.post(f"/courses/{course_id}/comments", json={"text": comment_text}, headers=headers)


def feed(client, headers, course_id, **params):
    return client.get(f"/courses/{course_id}/activity", headers=headers, params=params)


def labels(entries):
    """Each feed entry as a short label: a comment shows its text, any other entry its action."""
    return [entry["details"].get("text", entry["action"]) for entry in entries]


# --- Every change is logged -----------------------------------------------------------------------


def test_every_change_to_a_course_adds_one_log_row_naming_who_made_it(client, db, make_user, auth_header):
    priya = make_user(email="priya@example.com", role=Role.INSTRUCTOR)
    daniel = make_user(email="daniel@example.com", role=Role.INSTRUCTOR)
    as_priya, as_daniel = auth_header(priya), auth_header(daniel)

    course_id = client.post("/courses", json=FIRE_SAFETY, headers=as_priya).json()["id"]
    client.put(f"/courses/{course_id}", json={**FIRE_SAFETY, "title": "Fire safety 2026"}, headers=as_daniel)
    lessons_url = f"/courses/{course_id}/lessons"
    alarms = client.post(lessons_url, json={"title": "Alarms", "content": "Text"}, headers=as_priya).json()["id"]
    exits = client.post(lessons_url, json={"title": "Exits", "content": "Text"}, headers=as_priya).json()["id"]
    client.put(f"{lessons_url}/{alarms}", json={"title": "Fire alarms", "content": "Text"}, headers=as_daniel)
    client.put(f"{lessons_url}/order", json={"lesson_ids": [exits, alarms]}, headers=as_priya)
    client.delete(f"{lessons_url}/{alarms}", headers=as_daniel)

    log = db.scalars(select(ActivityLog).where(ActivityLog.course_id == course_id).order_by(ActivityLog.id)).all()
    assert [(entry.action, entry.actor_id) for entry in log] == [
        (Action.CREATED, priya.id),
        (Action.EDITED, daniel.id),
        (Action.LESSON_ADDED, priya.id),
        (Action.LESSON_ADDED, priya.id),
        (Action.LESSON_EDITED, daniel.id),
        (Action.LESSONS_REORDERED, priya.id),
        (Action.LESSON_REMOVED, daniel.id),
    ]
    assert all(entry.created_at is not None for entry in log)


# --- The database refuses to rewrite the log -------------------------------------------------------
# The app has no code that edits or deletes log rows. These tests go around the app and talk
# to the database directly, to show the trigger from migration 0002 refuses even then.


def test_the_database_refuses_to_change_a_log_row(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(update(ActivityLog).where(ActivityLog.course_id == course_id).values(action="edited"))


def test_the_database_refuses_to_delete_a_log_row(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(delete(ActivityLog).where(ActivityLog.course_id == course_id))


def test_the_database_refuses_to_empty_the_log(db, course_id):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("TRUNCATE activity_log"))


# --- The database checks the action (migration 0003) ----------------------------------------------


def test_the_database_refuses_an_unknown_action(db, instructor, course_id):
    db.add(ActivityLog(course_id=course_id, actor_id=instructor.id, action="deleted", details={}))

    with pytest.raises(IntegrityError, match="ck_activity_log_action_allowed"):
        db.flush()


def test_the_database_accepts_every_action_the_code_defines(db, instructor, course_id):
    """If someone adds an action to the code but not to the database check, this test fails."""
    db.add_all(ActivityLog(course_id=course_id, actor_id=instructor.id, action=action, details={}) for action in Action)

    db.flush()  # raises IntegrityError if any action is missing from the check


# --- Comments -------------------------------------------------------------------------------------


def test_a_comment_is_trimmed_and_saved_as_a_log_row(client, db, instructor, auth_header, course_id):
    response = comment(client, auth_header(instructor), course_id, "  Read lesson 2 first.  ")

    assert response.status_code == 201
    entry = response.json()
    assert entry["action"] == "commented"
    assert entry["details"] == {"text": "Read lesson 2 first."}
    assert entry["actor"] == {"id": instructor.id, "full_name": "Priya Shah", "role": "instructor"}
    saved = db.get(ActivityLog, entry["id"])
    assert (saved.course_id, saved.actor_id, saved.action) == (course_id, instructor.id, Action.COMMENTED)


@pytest.mark.parametrize("comment_text", ["   ", "x" * 2001], ids=["blank", "2001 characters"])
def test_a_blank_or_too_long_comment_is_rejected(client, db, instructor, auth_header, course_id, comment_text):
    response = comment(client, auth_header(instructor), course_id, comment_text)

    assert response.status_code == 422
    assert db.scalar(select(ActivityLog).where(ActivityLog.action == Action.COMMENTED)) is None


def test_a_comment_of_exactly_2000_characters_is_accepted(client, instructor, auth_header, course_id):
    response = comment(client, auth_header(instructor), course_id, "x" * 2000)

    assert response.status_code == 201


def test_an_enrolled_learner_can_comment(client, instructor, learner, auth_header):
    course_id = publish_new_course(client, auth_header(instructor))
    enroll(client, auth_header(learner), course_id)

    response = comment(client, auth_header(learner), course_id, "Is the east exit still blocked?")

    assert response.status_code == 201
    assert response.json()["actor"] == {"id": learner.id, "full_name": "Alex Chen", "role": "learner"}


def test_a_learner_who_can_see_the_course_but_is_not_enrolled_gets_403(client, db, instructor, learner, auth_header):
    course_id = publish_new_course(client, auth_header(instructor))
    as_learner = auth_header(learner)

    commenting = comment(client, as_learner, course_id, "Can I ask something first?")
    reading = feed(client, as_learner, course_id)

    assert commenting.status_code == reading.status_code == 403
    assert commenting.json() == reading.json() == {"detail": "Enrol in this course to join the discussion."}
    assert db.scalar(select(ActivityLog).where(ActivityLog.action == Action.COMMENTED)) is None


def test_an_enrolled_learner_can_comment_on_and_read_an_archived_course(client, instructor, learner, auth_header):
    as_instructor, as_learner = auth_header(instructor), auth_header(learner)
    course_id = publish_new_course(client, as_instructor)
    enroll(client, as_learner, course_id)
    client.post(f"/courses/{course_id}/archive", headers=as_instructor)

    commenting = comment(client, as_learner, course_id, "Will this come back next year?")
    reading = feed(client, as_learner, course_id)

    assert commenting.status_code == 201
    assert reading.status_code == 200
    assert labels(reading.json()) == ["Will this come back next year?"]


def test_a_learner_gets_the_same_404_when_commenting_on_a_draft_an_archived_or_a_missing_course(
    client, instructor, learner, auth_header, course_id
):
    archived_course_id = archive_new_course(client, auth_header(instructor))
    as_learner = auth_header(learner)

    responses = [comment(client, as_learner, course, "Hello?") for course in (course_id, archived_course_id, 999999)]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert responses[0].json() == responses[1].json() == responses[2].json()


def test_an_instructor_can_comment_on_an_archived_course(client, instructor, auth_header):
    course_id = archive_new_course(client, auth_header(instructor))

    response = comment(client, auth_header(instructor), course_id, "Archived until the 2027 rewrite.")

    assert response.status_code == 201


def test_commenting_on_a_course_that_does_not_exist_is_404(client, instructor, auth_header):
    response = comment(client, auth_header(instructor), 999999, "Hello?")

    assert response.status_code == 404


def test_the_database_refuses_to_change_a_comment(client, db, instructor, auth_header, course_id):
    comment_id = comment(client, auth_header(instructor), course_id, "Original").json()["id"]

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(update(ActivityLog).where(ActivityLog.id == comment_id).values(details={"text": "Rewritten"}))


def test_the_database_refuses_to_delete_a_comment(client, db, instructor, auth_header, course_id):
    comment_id = comment(client, auth_header(instructor), course_id, "Original").json()["id"]

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(delete(ActivityLog).where(ActivityLog.id == comment_id))


# --- The activity feed ----------------------------------------------------------------------------


def test_instructors_see_every_entry_newest_first_with_who_made_it(client, instructor, learner, auth_header):
    as_instructor = auth_header(instructor)
    course_id = publish_new_course(client, as_instructor)
    enroll(client, auth_header(learner), course_id)  # enrolling isn't a change to the course, so it isn't logged
    comment(client, auth_header(learner), course_id, "When is the next fire drill?")
    comment(client, as_instructor, course_id, "Next Tuesday.")
    client.post(f"/courses/{course_id}/archive", headers=as_instructor)

    response = feed(client, as_instructor, course_id)

    assert response.status_code == 200
    entries = response.json()
    assert [(entry["action"], entry["actor"]["full_name"], entry["actor"]["role"]) for entry in entries] == [
        ("archived", "Priya Shah", "instructor"),
        ("commented", "Priya Shah", "instructor"),
        ("commented", "Alex Chen", "learner"),
        ("published", "Priya Shah", "instructor"),
        ("lesson_added", "Priya Shah", "instructor"),
        ("created", "Priya Shah", "instructor"),
    ]
    ids = [entry["id"] for entry in entries]
    assert ids == sorted(ids, reverse=True)
    assert all(entry["created_at"] for entry in entries)


def test_learners_see_only_the_comments(client, instructor, learner, auth_header):
    as_instructor = auth_header(instructor)
    course_id = publish_new_course(client, as_instructor)
    enroll(client, auth_header(learner), course_id)
    comment(client, auth_header(learner), course_id, "When is the next fire drill?")
    comment(client, as_instructor, course_id, "Next Tuesday.")

    response = feed(client, auth_header(learner), course_id)

    assert response.status_code == 200
    assert [(entry["details"]["text"], entry["actor"]["role"]) for entry in response.json()] == [
        ("Next Tuesday.", "instructor"),
        ("When is the next fire drill?", "learner"),
    ]


def test_a_learner_gets_the_same_404_for_the_feed_of_a_draft_an_archived_or_a_missing_course(
    client, instructor, learner, auth_header, course_id
):
    archived_course_id = archive_new_course(client, auth_header(instructor))
    as_learner = auth_header(learner)

    responses = [feed(client, as_learner, course) for course in (course_id, archived_course_id, 999999)]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert responses[0].json() == responses[1].json() == responses[2].json()


def test_reading_the_feed_of_a_course_that_does_not_exist_is_404(client, instructor, auth_header):
    response = feed(client, auth_header(instructor), 999999)

    assert response.status_code == 404


def test_the_feed_pages_with_limit_and_before(client, instructor, auth_header, course_id):
    as_instructor = auth_header(instructor)
    for number in range(1, 6):
        comment(client, as_instructor, course_id, f"Comment {number}")

    first_page = feed(client, as_instructor, course_id, limit=4).json()
    second_page = feed(client, as_instructor, course_id, limit=4, before=first_page[-1]["id"]).json()

    assert labels(first_page) == ["Comment 5", "Comment 4", "Comment 3", "Comment 2"]
    assert labels(second_page) == ["Comment 1", "created"]  # shorter than the limit: nothing older is left


def test_a_page_holds_50_entries_unless_asked_otherwise(client, db, instructor, auth_header, course_id):
    db.add_all(
        ActivityLog(course_id=course_id, actor_id=instructor.id, action=Action.COMMENTED, details={"text": str(n)})
        for n in range(60)
    )
    db.commit()

    response = feed(client, auth_header(instructor), course_id)

    assert len(response.json()) == 50


@pytest.mark.parametrize("limit", [0, 101])
def test_the_page_size_must_be_between_1_and_100(client, instructor, auth_header, course_id, limit):
    response = feed(client, auth_header(instructor), course_id, limit=limit)

    assert response.status_code == 422


def test_a_page_takes_the_same_number_of_queries_however_many_people_are_on_it(
    client, db, make_user, instructor, auth_header, recorded_sql
):
    """A page's actors are loaded together with its entries, not with one query per entry."""
    as_instructor = auth_header(instructor)
    learner_headers = [auth_header(make_user(email=f"learner{n}@example.com", role=Role.LEARNER)) for n in range(10)]

    def queries_to_read_a_page_with_comments_from(commenters):
        course_id = publish_new_course(client, as_instructor)
        for headers in commenters:
            enroll(client, headers, course_id)
            comment(client, headers, course_id, "Hello")
        # Empty the session's cache first. Otherwise the users created above would come from memory,
        # and even one-query-per-entry code would send no extra queries.
        db.expunge_all()
        with recorded_sql() as statements:
            response = feed(client, as_instructor, course_id)
        assert len(response.json()) == len(commenters) + 3  # the comments, plus created, lesson_added, published
        return len(statements)

    assert queries_to_read_a_page_with_comments_from(learner_headers[:2]) == (
        queries_to_read_a_page_with_comments_from(learner_headers)
    )
