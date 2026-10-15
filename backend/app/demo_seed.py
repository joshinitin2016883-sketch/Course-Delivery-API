"""Demo data, so every page has something to show: more learners, courses in every status, enrolments in
every state, completions over the last 8 weeks, quiet learners for the alerts, and a few comments.
Run with  python -m app.seed --demo  (see seed.py).

Every time is placed relative to the moment the seed runs, by the database's clock. So the numbers drift as
days pass: completions slide out of the 8-week chart and more learners go quiet. Re-seed before a demo.

The API can only record "now", so rows are inserted directly, with past times. They are kept exactly as the
services would have left them (tests/test_demo_seed.py checks every enrolment), and the activity log gets the
rows the services would have written, in time order. Nothing is ever updated or deleted: the activity log is
append-only, so its past times are set when each row is inserted.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Action,
    ActivityLog,
    AlertDismissal,
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonCompletion,
    Role,
    User,
)

PRIYA, DANIEL = "instructor@example.com", "instructor2@example.com"

EXTRA_LEARNERS = [
    ("aisha@example.com", "Aisha Bello"),
    ("ben@example.com", "Ben Carter"),
    ("chloe@example.com", "Chloe Martin"),
    ("diego@example.com", "Diego Ramos"),
    ("emma@example.com", "Emma Wilson"),
    ("felix@example.com", "Felix Wagner"),
    ("grace@example.com", "Grace Kim"),
    ("hiro@example.com", "Hiro Tanaka"),
    ("isla@example.com", "Isla Murphy"),
    ("jamal@example.com", "Jamal Hussain"),
    ("kate@example.com", "Kate Novak"),
    ("liam@example.com", "Liam Byrne"),
    ("mei@example.com", "Mei Lin"),
    ("noah@example.com", "Noah Schmidt"),
    ("olivia@example.com", "Olivia Rossi"),
    ("pedro@example.com", "Pedro Alves"),
    ("quinn@example.com", "Quinn Adams"),
    ("ravi@example.com", "Ravi Patel"),
    ("sofia@example.com", "Sofia Andersson"),
    ("tom@example.com", "Tom Fischer"),
]

# (title, category, author, status, description, lesson titles). Every course has at least two lessons, so a
# learner can be part-way through any of them.
COURSES = [
    ("Fire safety basics", "compliance", PRIYA, CourseStatus.PUBLISHED,
     "What to do when the alarm sounds, and how to stop fires starting.",
     ["Why fires start", "Raising the alarm", "Evacuation routes"]),
    ("Data protection essentials", "compliance", DANIEL, CourseStatus.PUBLISHED,
     "Handling personal data safely, and what to do if something goes wrong.",
     ["What counts as personal data", "Keeping data safe", "Retention periods", "Reporting a breach"]),
    ("Welcome to the team", "onboarding", PRIYA, CourseStatus.PUBLISHED,
     "Your first week: the people, the tools, and where to find help.",
     ["Who's who", "Our tools", "Getting help"]),
    ("Python for analysts", "skills", DANIEL, CourseStatus.PUBLISHED,
     "Write small scripts to clean and summarise data.",
     ["Setting up", "Reading a CSV", "Cleaning data", "Grouping and totals", "Your own data"]),
    ("Giving useful feedback", "skills", PRIYA, CourseStatus.PUBLISHED,
     "How to give feedback that is specific, kind and easy to act on.",
     ["Why feedback matters", "Being specific", "Following up"]),
    ("Advanced negotiation", "skills", DANIEL, CourseStatus.DRAFT,
     "Not ready yet: still being written.",
     ["Preparing", "Opening offers"]),
    ("Old expenses policy", "compliance", PRIYA, CourseStatus.ARCHIVED,
     "Replaced by the new expenses policy. Kept so past learners can still read it.",
     ["What you can claim", "How to claim"]),
]

# Learners who went quiet: (learner, course, days since their last completed lesson). The first alert has
# already been dismissed by Priya, so 4 alerts show.
QUIET = [
    ("sofia@example.com", "Data protection essentials", 31),
    ("learner@example.com", "Python for analysts", 25),
    ("jordan@example.com", "Fire safety basics", 21),
    ("kate@example.com", "Giving useful feedback", 18),
    ("diego@example.com", "Welcome to the team", 16),
]

# (course, author, days ago, text). Learners only comment on a course they are in (they are all in QUIET).
COMMENTS = [
    ("Fire safety basics", PRIYA, 40, "Reminder: the fire drill is on the first Monday of each month."),
    ("Fire safety basics", "jordan@example.com", 24, "Where is the assembly point for the second building?"),
    ("Fire safety basics", PRIYA, 23, "Car park B, by the gate. I've added it to the evacuation lesson."),
    ("Python for analysts", DANIEL, 30, "Bring a CSV of your own for the last lesson."),
    ("Python for analysts", "learner@example.com", 27, "Is pandas installed on the shared laptops?"),
    ("Data protection essentials", DANIEL, 12, "The retention periods lesson now follows the new policy."),
]

CREATED_DAYS_AGO, PUBLISHED_DAYS_AGO, ARCHIVED_DAYS_AGO = 70, 65, 20


def add_demo_data(db: Session, password_hash: str) -> str | None:
    """Add the demo data and say what was added, or do nothing and return None if any course exists already:
    the demo data only goes into a database with no courses, so it never mixes with real ones.
    The demo accounts (seed.py) must exist first. New learners get the same password as them."""
    if db.scalar(select(func.count()).select_from(Course)) > 0:
        return None
    now = db.scalar(select(func.now()))
    rng = random.Random(2026)  # a fixed seed: the same data every time, apart from the dates

    users = _users(db, password_hash)
    learners = [user for user in users.values() if user.role == Role.LEARNER]
    for number, (title, category, author, status, description, lesson_titles) in enumerate(COURSES):
        created_at = now - timedelta(days=CREATED_DAYS_AGO) + timedelta(hours=number)  # an hour apart
        course = Course(title=title, description=description, category=category, status=status,
                        instructor_id=users[author].id, created_at=created_at)
        db.add(course)
        db.flush()  # sends the INSERT now, so course.id exists for the lessons and the log
        log = [(created_at, users[author], Action.CREATED,
                {"title": title, "description": description, "category": category})]
        lessons = []
        for position, lesson_title in enumerate(lesson_titles, start=1):
            added_at = created_at + timedelta(minutes=position)
            lesson = Lesson(course_id=course.id, title=lesson_title, content=f"{lesson_title}: the lesson text.",
                            position=position, created_at=added_at)
            db.add(lesson)
            db.flush()
            lessons.append(lesson)
            log.append((added_at, users[author], Action.LESSON_ADDED,
                        {"lesson_id": lesson.id, "title": lesson_title, "position": position}))
        if status != CourseStatus.DRAFT:
            log.append((now - timedelta(days=PUBLISHED_DAYS_AGO), users[author], Action.PUBLISHED,
                        {"from": "draft", "to": "published"}))
            _add_enrolments(db, rng, now, course, lessons, learners, users)
        if status == CourseStatus.ARCHIVED:
            log.append((now - timedelta(days=ARCHIVED_DAYS_AGO), users[author], Action.ARCHIVED,
                        {"from": "published", "to": "archived"}))
        for course_title, author_email, days_ago, text in COMMENTS:
            if course_title == title:
                log.append((now - timedelta(days=days_ago), users[author_email], Action.COMMENTED, {"text": text}))
        # In time order, so the ids run in the same order as the times, as they would have when it happened.
        for at, actor, action, details in sorted(log, key=lambda entry: entry[0]):
            db.add(ActivityLog(course_id=course.id, actor_id=actor.id, action=action, details=details,
                               created_at=at))
        db.flush()

    _dismiss_first_quiet_alert(db, now, users)
    db.commit()
    return (f"Added {len(EXTRA_LEARNERS)} learners, {len(COURSES)} courses, "
            f"{db.scalar(select(func.count()).select_from(Enrollment))} enrolments and {len(COMMENTS)} comments.")


def _users(db: Session, password_hash: str) -> dict[str, User]:
    """Every user by email, after adding the extra learners that don't exist yet."""
    existing = {user.email for user in db.scalars(select(User))}
    for email, full_name in EXTRA_LEARNERS:
        if email not in existing:
            db.add(User(email=email, full_name=full_name, role=Role.LEARNER, password_hash=password_hash))
    db.flush()
    return {user.email: user for user in db.scalars(select(User))}


def _add_enrolments(db, rng, now, course, lessons, learners, users) -> None:
    """Enrol a random group of learners in the course, each in a random state, plus the course's quiet
    learners. In an archived course, all progress happened before it was archived."""
    quiet = {users[email].id: days for email, title, days in QUIET if title == course.title}
    others = [learner for learner in learners if learner.id not in quiet]
    for learner in rng.sample(others, rng.randint(9, 14)):
        status = rng.choices(list(EnrollmentStatus), weights=[2, 4, 3])[0]
        if course.status == CourseStatus.ARCHIVED:
            archived_at = now - timedelta(days=ARCHIVED_DAYS_AGO)
            enrolled_at = archived_at - timedelta(days=rng.uniform(10, 30))
            last = _between(rng, enrolled_at, archived_at)
        elif status == EnrollmentStatus.NOT_STARTED:
            enrolled_at = now - timedelta(days=rng.uniform(1, 50))
            last = None
        elif status == EnrollmentStatus.IN_PROGRESS:
            # Active in the last 10 days, so only the QUIET learners raise alerts.
            enrolled_at = now - timedelta(days=rng.uniform(12, 50))
            last = now - timedelta(days=rng.uniform(0.2, 10))
        else:
            # Completions inside the dashboard's 8 weeks.
            enrolled_at = now - timedelta(days=rng.uniform(5, 50))
            last = _between(rng, enrolled_at, now)
        _enrol(db, rng, course, lessons, learner, status, enrolled_at, last)
    for learner_id, days in quiet.items():
        last = now - timedelta(days=days)
        enrolled_at = last - timedelta(days=rng.uniform(5, 12))  # before their COMMENTS, too
        _enrol(db, rng, course, lessons, db.get(User, learner_id), EnrollmentStatus.IN_PROGRESS, enrolled_at, last)


def _enrol(db, rng, course, lessons, learner, status, enrolled_at, last) -> None:
    """One enrolment and its lesson completions, as complete_lesson would have left them: lessons done in
    order, the first completion is started_at, the latest (`last`) is last_activity_at, and finishing the
    last lesson is completed_at."""
    done = {
        EnrollmentStatus.NOT_STARTED: 0,
        EnrollmentStatus.IN_PROGRESS: rng.randint(1, len(lessons) - 1),
        EnrollmentStatus.COMPLETED: len(lessons),
    }[status]
    times = sorted(_between(rng, enrolled_at, last) for _ in range(done - 1)) + [last] if done else []
    enrollment = Enrollment(course_id=course.id, user_id=learner.id, enrolled_by=learner.id, status=status,
                            enrolled_at=enrolled_at)
    if times:
        enrollment.started_at = times[0]
        enrollment.last_activity_at = times[-1]
    if status == EnrollmentStatus.COMPLETED:
        enrollment.completed_at = times[-1]
    db.add(enrollment)
    db.flush()
    for lesson, completed_at in zip(lessons, times):
        db.add(LessonCompletion(enrollment_id=enrollment.id, lesson_id=lesson.id, completed_at=completed_at))


def _dismiss_first_quiet_alert(db: Session, now: datetime, users: dict[str, User]) -> None:
    """Priya dismissed the first QUIET learner's alert two days ago, so the alerts page shows a dismissal."""
    email, title, _ = QUIET[0]
    enrollment = db.scalar(
        select(Enrollment).join(Course).where(Course.title == title, Enrollment.user_id == users[email].id)
    )
    db.add(AlertDismissal(enrollment_id=enrollment.id, quiet_since=enrollment.last_activity_at,
                          dismissed_by=users[PRIYA].id, dismissed_at=now - timedelta(days=2)))


def _between(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """A random moment from start to end."""
    return start + (end - start) * rng.random()
