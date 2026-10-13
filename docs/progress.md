# Progress: what's complete

Status on 13 October 2026. Steps 1 and 2 of the build plan are finished: the backend for sign-in,
courses, lessons and the activity log. There is no frontend and no deployment yet.

## The ten goals

| # | Goal | Status | What's done |
|---|------|--------|-------------|
| 1 | Accounts and roles | Partial | Email and password sign-in. Instructor and learner roles, checked on the server for every course and lesson endpoint. The enrolment and progress permissions arrive with goals 4 and 5. |
| 2 | Courses | Partial | Instructors create and edit courses (title, description, category). Archive and restore are not built yet. |
| 3 | Lessons inside courses | Done (API) | Lessons are added, edited, reordered and removed; opening a course returns its lessons in running order. |
| 4 | Course and progress states | Not started | The status column exists and every course starts as a draft, but no moves between states yet. Progress states come with enrolment. |
| 5 | Enrolment | Not started | |
| 6 | Finding courses | Not started | |
| 7 | Bulk enrolment and CSV export | Not started | |
| 8 | Dashboard | Not started | |
| 9 | History you cannot rewrite | Partial | Every course change writes a log row saying who did what and when, and the database refuses to edit or delete log rows. Not yet: publish and archive entries, comments, and an endpoint that reads the log. |
| 10 | Inactivity alerts | Not started | |

"Done (API)" means the server side is finished and tested. No goal has a user interface yet.

## Step 1: backend scaffold, sign-in and roles

- FastAPI on Python 3.12, SQLAlchemy 2.0 and Alembic, with exact dependency versions in `backend/requirements.txt`.
- Postgres 17 in Docker: a development database on port 5433 and a separate test database on port 5434.
- Settings and secrets come only from environment variables (`backend/.env` locally; names listed in `backend/.env.example`).
- `users` table: email (unique, stored trimmed and lower-case), full name, role (`instructor` or `learner`) and a bcrypt password hash.
- Signing in returns a JWT that expires after 8 hours and holds only the user id. The role is read from the database on every request.
- Seed script (`python -m app.seed`) creates 2 demo instructors and 5 demo learners, all with the password in `SEED_PASSWORD`.
- `README.md` has the local setup steps. The assignment brief moved to `docs/brief.md`, unchanged.

## Step 2: courses, lessons and the activity log

- `courses` table: title, description, category (`onboarding`, `compliance` or `skills`), status (starts as `draft`) and the instructor who created it.
- `lessons` table: title, content and a position. Positions always run 1, 2, 3 with no gaps.
- `activity_log` table: one row per change, holding the course, who made the change, what changed (old and new values) and when.

Rules the server enforces:

- Only instructors create or change courses and lessons; learners get 403. Any instructor can edit any course.
- Learners only see published courses. Any other course answers 404, so a learner can't tell a draft exists.
- A new course is always a draft, whatever the request says.
- A new lesson goes to the end of the course.
- A reorder must list every lesson of the course exactly once, or it is rejected with 409. A successful reorder writes one log row.
- Removing a lesson closes the gap in the positions, and the log keeps the removed lesson's title.
- Saving without a real change writes no log row.
- A change and its log row are saved in the same transaction: either both are saved or neither is.
- Every lesson change locks the course row first, so two changes to the same course's lessons run one after the other.

Rules the database itself enforces:

- Role, status and category can only take their allowed values.
- No two users share an email, and emails are stored trimmed and lower-case.
- No two lessons of a course share a position, and positions start at 1.
- A trigger refuses any UPDATE, DELETE or TRUNCATE on `activity_log`, even from the database superuser.

## API endpoints available now

| Method | Path | Who may call it | What it does |
|--------|------|-----------------|--------------|
| GET | `/health` | anyone | health check |
| POST | `/auth/login` | anyone | email and password in, token out |
| GET | `/auth/me` | signed in | the signed-in user |
| POST | `/courses` | instructors | create a draft course |
| GET | `/courses/{id}` | instructors; learners only for a published course | the course with its lessons in order |
| PUT | `/courses/{id}` | instructors | edit title, description and category |
| POST | `/courses/{id}/lessons` | instructors | add a lesson at the end |
| PUT | `/courses/{id}/lessons/{lesson_id}` | instructors | edit a lesson |
| DELETE | `/courses/{id}/lessons/{lesson_id}` | instructors | remove a lesson |
| PUT | `/courses/{id}/lessons/order` | instructors | put all of a course's lessons in a new order |

## Database migrations

- `0001`: the `users` table.
- `0002`: the `courses`, `lessons` and `activity_log` tables, and the append-only trigger.

Both migrations have been run up, down and up again cleanly.

## Tests

60 tests, all passing. Run `python -m pytest` from `backend/`. The test database is rebuilt from the migrations at the start of every run, and each test is rolled back afterwards.

| File | Tests | What they cover |
|------|-------|-----------------|
| `test_auth.py` | 17 | sign-in; missing, malformed, forged, unsigned, expired and deleted-user tokens; password hashing; constraints on the users table |
| `test_courses.py` | 22 | creating, viewing and editing courses; permissions; validation; log rows; the one-transaction rule; database constraints |
| `test_lessons.py` | 17 | adding, editing, removing and reordering lessons; positions; permissions; log rows; database constraints |
| `test_activity_log.py` | 4 | one log row per change naming the right person; the database refusing to edit, delete or empty the log |

Also checked by hand against the running server: sign-in, every endpoint above, reordering and removing lessons with real commits, and editing or deleting log rows directly in `psql`, which the database refused.

## Not complete yet

- Course states (publish, archive, restore), reading the log and comments. This is step 3, planned but not started.
- Enrolment and learner progress, course search and filters, bulk enrolment and CSV export, inactivity alerts, the dashboard.
- The frontend, demo data beyond the user accounts, and deployment (Neon, Render, Vercel).
- `docs/architecture.md`, `docs/schema.md`, `docs/plan.md`, `docs/decisions.md`, `docs/ai-prompts.md` and `SUBMISSION.md` are still the blank stubs from the assignment.
- The test run shows one warning: Starlette is phasing out `httpx` in its test client. Swapping to `httpx2` is agreed but not done.
