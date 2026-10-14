# Schema

Six tables, built by migrations 0001–0005. The models in `backend/app/models` match them. In the tables below, → marks a foreign key.

## Tables

### users

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. |
| email | varchar(254) | Unique. Stored trimmed and lower-case, and a CHECK refuses anything else. |
| full_name | varchar(100) | |
| role | varchar(20) | `instructor` or `learner` (CHECK). |
| password_hash | varchar(100) | bcrypt. The API never returns it. |
| created_at | timestamptz | Defaults to now(). |

### courses

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. |
| title | varchar(200) | |
| description | text | |
| category | varchar(20) | `onboarding`, `compliance` or `skills` (CHECK). |
| status | varchar(20) | `draft`, `published` or `archived` (CHECK). Starts as `draft`. |
| instructor_id | integer | → users. Who created it; any instructor can manage it (Decision 3). |
| created_at | timestamptz | |

### lessons

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. |
| course_id | integer | → courses. |
| title | varchar(200) | |
| content | text | Plain text (Decision 28). |
| position | integer | 1, 2, 3… within the course, at least 1 (CHECK). Unique per course, checked at commit so a reorder can renumber in one transaction. |
| created_at | timestamptz | |

### activity_log

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. Also the feed's order and paging key (Decision 9). |
| course_id | integer | → courses. Indexed together with id, for one course's feed. |
| actor_id | integer | → users. Who did it. |
| action | varchar(30) | One of ten actions, such as `published` or `commented` (CHECK, Decision 10). |
| details | jsonb | What changed, e.g. `{"title": {"from": "Old", "to": "New"}}`, or a comment's text. Defaults to `{}`. |
| created_at | timestamptz | |

A trigger refuses UPDATE, DELETE and TRUNCATE on this table (Decision 6).

### enrollments

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. |
| course_id | integer | → courses. |
| user_id | integer | → users: the learner. Indexed, for My courses. |
| status | varchar(20) | `not_started`, `in_progress` or `completed` (CHECK). |
| enrolled_by | integer | → users. The learner themselves for now; an instructor once bulk enrolment exists. |
| enrolled_at | timestamptz | |
| started_at | timestamptz, null | Set by the first completion. Null exactly when the status is `not_started` (CHECK). |
| completed_at | timestamptz, null | Set exactly when the status is `completed` (CHECK). |
| last_activity_at | timestamptz, null | The latest completion. Null exactly when started_at is (CHECK). |

One enrolment per learner per course (unique on course_id and user_id). Also indexed on course_id and status together.

### lesson_completions

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key. |
| enrollment_id | integer | → enrollments. |
| lesson_id | integer | → lessons, ON DELETE RESTRICT (Decision 15). Indexed (migration 0005). |
| completed_at | timestamptz | |

One row per lesson per enrolment (unique on enrollment_id and lesson_id).

The alert dismissals table arrives with goal 10.

## Relationships

- **One-to-many:** a course has many lessons and many activity log rows, and an enrolment has many lesson completions. Also, a user creates many courses (as instructor) and makes many log entries (as actor), and a lesson has many completions.
- **Many-to-many:** learners and courses, through enrollments. Each pair appears once, and the enrolment row holds that learner's state and times in that course.

## Rules: database or services

The database enforces what must be true of the data whoever writes it, including when two requests arrive at the same moment:

- Allowed values: role, category, course status, enrolment status and log action (CHECKs).
- Uniqueness:
  - one account per email, compared trimmed and lower-case;
  - one enrolment per learner per course, which is the race-safe "already enrolled" check (Decision 18);
  - one completion per lesson per enrolment;
  - one lesson per position in a course.
- An enrolment's status agrees with its timestamps (three CHECKs, Decision 14).
- History can't be rewritten. The trigger keeps the log append-only (Decision 6), and the RESTRICT foreign key stops a completed lesson being deleted (Decision 15).

The services enforce rules that depend on who is asking, compare several rows, or need a message a person can act on:

- Roles: only instructors create and edit courses and lessons; only learners enrol and complete lessons (Decision 3).
- State moves:
  - the table of course moves; publishing or restoring needs a lesson, and a published course keeps its last lesson (Decision 5);
  - progress only moves Not started → In progress → Completed, including when lessons change (Decisions 14 and 16).
- Visibility: learners see published courses plus archived ones they're enrolled in, and lesson content only after enrolling (Decisions 17 and 19). Joining the discussion needs an enrolment (Decision 20).
- Archived courses are read-only, positions stay 1…n with no gaps (Decision 11), and every course change writes its log row in the same transaction.
- Two changes at once can't break these rules, because every change locks the course row first (Decision 7).

Why I drew the line there: a database rule is a backstop that a script, a new endpoint or a bug can't get round. Only the database can stop two simultaneous requests both passing a uniqueness check. But a CHECK can't know who is asking or answer with a helpful 403 or 409. A rule that spans several rows, such as whether the course still has a lesson, is also clearer in Python under a row lock than in a trigger. Where a rule matters most, both enforce it: the service gives the message, and the database refuses if the service is ever wrong.

## What I denormalised

Very little, and nothing that can drift:

- **The activity log copies names and values into `details`.** That's a lesson's title and position when it's added or removed, and a field's old and new value on an edit. The log then still reads correctly after the lesson is deleted or the course is edited again (Decision 12). Log rows never change, so the copies never need updating.
- **An enrolment's `started_at` and `last_activity_at` repeat its first and latest completion times,** which `lesson_completions` also holds. They're kept on the row so the database can tie each status to its times (Decision 14), and so the coming inactivity alerts (goal 10) can find quiet learners without scanning completions. They're written in the same transaction as the completion, under the enrolment's row lock.

Counts aren't stored. Enrolment counts (Decision 25) and lessons done and total are counted when read.

## At 100x the data

1. **Sorting by enrolment count** slows down first. The list counts every matching course's enrolments before it can choose a page (Decision 25). Fix: a small counts table, kept up to date in the enrolment's transaction without touching the course row.
2. **Search** is `ILIKE '%text%'`, which can't use an ordinary index, so every search reads the whole courses table (Decision 24). Fix: a pg_trgm GIN index on title and description, with the query unchanged.
3. **Deep pages** use OFFSET, so page 500 makes Postgres read and throw away about 10,000 rows first, and the total is a separate COUNT over every match. Fix: keyset paging, where each page starts after the last row of the one before (`WHERE (sort value, id) < (last row's)`). The id tie-breaker already makes that possible (Decision 26), and the activity feed already pages this way (Decision 9).

The rest holds up. The log feed and My courses read through indexes, and a learner's completions are found through the unique index that starts with enrollment_id.
