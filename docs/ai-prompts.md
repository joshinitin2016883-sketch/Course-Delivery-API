
# AI prompts

## How I used AI

I used two tools. Claude Code, the coding agent, worked in my repo: it wrote the code and the tests and ran them. Claude in a chat window helped me plan the build, review each of the agent's reports, and draft the longer prompts below. I edited every prompt before sending it, made every design call myself, checked each change and committed it myself.

The prompts below are the ones I sent to the coding agent, copied from its chat in order. Long ones are folded; click to open them.

One habit I picked up: the agent won't act on a message that is only pasted text, because pasted text could come from anywhere. It treated my pasted notes as plans only, twice, until I typed something myself. Since then I type one line of my own above every paste.

## 1. Setting up the project and the working rules

### Prompt

My opening message: what the project is, the stack, that I'm on Windows and must run Python tools as `python -m`, and how I want the agent to work (I make the design calls, plan before changing files, rules enforced on the server, tests for every rule, never commit or push).

<details>
<summary>Full prompt</summary>

```text
I'm building a take-home assignment: an internal course delivery and enrolment system that replaces a spreadsheet. Instructors build and publish courses, learners enrol and work through lessons, and progress is tracked automatically.
I'll have to explain every line of this on a review call, so keep the code simple and readable rather than clever.

The full brief is in docs/brief.md. Its "What it must do" section is the spec, and the exact wording matters.
My design decisions so far are in docs/decisions.md. Follow them, and don't reopen them unless I ask.

#detail 
-
Backend: FastAPI on Python 3.12, SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt
- Database: PostgreSQL on Neon
- Frontend: React with Vite and Tailwind; Recharts for the one chart
- Hosting: Render for the API, Vercel for the frontend
I'm on Windows, and Application Control blocks the .exe launchers that pip installs. Always run Python tools as python -m pip, python -m uvicorn, python -m alembic and python -m pytest.
backend/app/{core,models,schemas,services,routers}, backend/tests, backend/alembic, frontend/src/{api,pages,components}
How I like you to work
- I make the design calls. When there's a real choice, lay out the options and trade-offs, then wait for me.
- Before changing anything, show me a short plan and the list of files, and stick to the files we agreed.
- Every permission and state rule is enforced on the server. Hiding a button in the UI doesn't count.
- Business rules live in services/. Routers only validate input and call a service.
- Every change to a course writes an activity_log row in the same transaction.
- Secrets come only from environment variables, never from code.
- Write pytest tests for every rule you implement, and run them before you tell me you're done.
- Never run git commit or git push. I commit myself after reviewing the change.
```

</details>

### What I got

Before building anything, the agent checked my claims against the repo and found three problems: the brief was in `README.md`, not `docs/brief.md`; `docs/decisions.md` was still the blank template; and my machine had only Python 3.14, with Docker not running and no git repository. It laid out the setup and design choices (S1–S3, D1–D6) with a recommendation for each.

### What I corrected

My own prompt was wrong about two files: I said my decisions were already in `docs/decisions.md`. I answered the agent's questions instead (section 2), and the brief was moved to `docs/brief.md`.

## 2. Step 1: sign-in and roles

### Prompt

```text
everything in project and also check for docker
```

"Everything" meant: take all its recommendations (Python 3.12 beside 3.14, Postgres in Docker, D1–D6).

### What I got

Step 1: Postgres 17 in Docker (dev and test databases), the users table, bcrypt passwords, an 8-hour JWT, `/auth/login` and `/auth/me`, the seed script, and 17 tests. Its report said httpx2 was "the successor to httpx, from the same author".

### What I corrected

That claim was wrong. I checked PyPI: httpx2 is Pydantic's fork of httpx. I told the agent (section 3), and it confirmed the mistake came from an author field the fork had inherited.

## 3. Reviewing step 1 and deciding step 2

### Prompt

My review of step 1, the httpx2 correction, my step 2 decisions (reorder with one request listing every lesson; hard-delete lessons for now; a rule for step 3), then "go".

<details>
<summary>Full prompt</summary>

```text
Thanks, step 1 looks solid. Two fixes before I commit:

1. The .gitignore only ignores venv/, not .venv/, so the virtual environment would get committed. Add .venv/ and .pytest_cache/ to it.
2. On the warning, go with (a): swap httpx for httpx2. One correction for my notes: httpx2 is Pydantic's fork of httpx, not a release from httpx's author. Starlette 1.x tries it first in the test client, which is why the warning appears. Then run the tests with -W error::DeprecationWarning to show the warning is gone.

Then help me commit step 1 as a few small commits instead of one. Don't run git yourself. Group the files into four to six commits in the order the work actually happened, each with a message, and give me the exact git add and git commit commands. The first commit should be the brief and the docs stubs, so the history starts from the assignment.

For step 2, here are my decisions, so you can plan while I commit:
- Reordering: (a). One request with every lesson id in the new order, checked against this course's lessons, renumbered in one transaction, with one log row.
- Removing a lesson: hard delete is fine for now, and the log keeps its title. Flag it as an open question for the enrolment step, because completions will point at lessons.
- Lessons before states is fine. But note this for step 3: removing the last lesson of a published course must be rejected with a 409, the same as publishing an empty course.

Show me the step 2 plan and wait for my go.
Committed. Go with step 2. When you're done, give me the same kind of report, including what I should check by hand.
```

</details>

### What I got

Step 2: courses, lessons in order, and an activity log that a Postgres trigger stops anyone from editing or deleting. 60 tests in total, plus a list of things to check by hand.

### What I corrected

This prompt contained my own mistake, `-W error::DeprecationWarning` (corrected in section 4). It also asked for small commits, but the project wasn't a git repository yet, so steps 1 and 2 ended up in one commit (explained in `plan.md`).

## 4. Planning step 3

### Prompt

My answers after checking step 2 by hand: a commit plan request, the httpx2 swap, and additions to step 3.

<details>
<summary>Full prompt</summary>

```text
Step 2 looks good, and I've checked it by hand. Answers first, then two additions to step 3.

Git: you're right, there's no repository. I'll delete the empty Project folder and run git init. Before you change any code, give me a commit plan for everything built so far, in the order it was built: step 1's commits first, then step 2's. Three files changed in both steps (main.py, models/__init__.py, services/errors.py). For those, tell me exactly which lines belong to step 1, so I can stage only those with git add -p. List the commands; don't run git yourself.

httpx2: yes. Make the swap as its own small change after I've committed, and rerun the tests with -W error::DeprecationWarning.

Step 3: option (a), one endpoint per move, all checked against one table of allowed moves. Also:
- Every move takes the same course-row lock as the lesson changes, so publishing a course and removing its last lesson can't both succeed at once.
- Test all nine combinations of the three states and three moves, not just the three legal ones.
- Archived courses are read-only: editing the course or its lessons returns a 409 with a clear message.

Add to step 3, because goal 9 isn't finished: the log is written, but nothing reads it, and comments don't exist yet.
- GET /courses/{id}/activity returns the log newest first, with who did each thing and when. Instructors only for now.
- POST /courses/{id}/comments, instructors only for now; enrolled learners join in at the enrolment step. A comment is a log row, so it can never be edited or deleted.
- Tests for both, including a learner being refused.

Show me the commit plan, then the step 3 plan and file list, and wait for my go.
```

</details>

### What I got

A nine-commit plan for steps 1 and 2, and a step 3 plan with two choices for me.

### What I corrected

The agent corrected two instructions of mine:

- `-W error::DeprecationWarning` would prove nothing: Starlette's warning inherits from `UserWarning`, so that run passes even with the warning present. We used `-W error`.
- `git add -p` doesn't work on untracked files: they need `git add -N` first, and a brand-new file is a single hunk.

I also changed two of my own decisions:

- I dropped the nine-commit plan. The file times showed steps 1 and 2 were each written in one burst, so nine commits would invent steps that never happened.
- I had said comments were "instructors only for now". The brief says learners leave comments too, so in the step 3 prompt learners can comment on courses they can see.

## 5. Two small requests

```text
only tell me envo name only
```

It listed the environment variable names.

```text
md file of what is complete
```

It wrote `docs/progress.md`: what is built, the rules the server and the database enforce, and what is left.

## 6. Step 3: course states, comments and the activity feed

### Prompt

The step 3 brief (moves, read-only archived courses, the last-lesson rule, comments, the feed, tests, and a two-terminal lock check), then my answers to its two questions, then "go".

<details>
<summary>The step 3 brief</summary>

```text
This message is step 3 of my build. Work through it in the order below and stop wherever it says to wait. If anything from earlier conversations or your saved knowledge disagrees with this message, this message wins.

## Context
I'm building "Assignment 05 – Course Delivery & Enrollment" (full brief in docs/brief.md). Backend only so far: FastAPI on Python 3.12, SQLAlchemy 2.0 (sync) with psycopg 3, Alembic, Pydantic v2, PyJWT, bcrypt.
- Postgres runs in Docker: dev on port 5433, tests on 5434. If the databases aren't running, `docker compose up -d` from backend/ starts both.
- This is Windows with PowerShell. The venv is backend/.venv: activate it, or call backend/.venv/Scripts/python.exe directly.
- Python tools run as `python -m ...` from backend/.
- The project path has spaces and brackets, so quote paths.

Built so far: step 1 (sign-in, 7 seeded users) and step 2 (courses, lessons, append-only activity log). 60 tests pass against a real Postgres test database built from the migrations. The test run shows one httpx deprecation warning; ignore it, because fixing it is a separate change.

Rules that always hold:
- Every permission and state rule is enforced on the server.
- Business rules live only in services/. Routers validate input and call a service.
- Every change to a course writes one activity_log row in the same transaction.
- Services raise errors, and main.py alone maps them to 401/403/404/409.
- The role is read from the database on every request.
- A learner asking for a course that isn't published gets 404.
- Secrets come only from environment variables.
- backend/.env and .venv are never committed.

Decisions already made (if you see a real problem with one, say so; otherwise build on them):
- D1 Bearer token in localStorage, 8-hour expiry, no refresh tokens.
- D2 Accounts come only from the seed script; bulk enrolment never creates accounts.
- D3 Any instructor can manage any course; courses.instructor_id records the author.
- D4 Category is a fixed list (onboarding, compliance, skills), stored as text with a CHECK.
- D5 Course states: Draft → Published needs at least one lesson; Published → Archived; restore Archived → Published re-checks lessons; Draft → Archived is rejected; archived courses are read-only.
- D6 activity_log is append-only. There are no update or delete code paths, and a trigger rejects UPDATE, DELETE and TRUNCATE. Edit rows store old and new values. Lessons are referenced in the JSON details, not by foreign key.
- Reorder is one PUT listing every lesson id. Lessons are hard-deleted, and the log keeps the title. Lesson changes lock the course row (SELECT ... FOR UPDATE).

How we work:
- I make every design call. For anything not decided here, give me options with a recommendation and wait.
- Before changing anything, show a short plan with the exact list of files (an Implementation Plan is fine) and wait for my approval.
- Write pytest tests for every rule, and run the full suite before calling a change done.
- I do all git work myself. Never commit, push or run any git command that changes the repo.
- After each change, give me a commit Summary and Description and the file list.

## Step 3: course states and finishing the activity log

Decided:

Moves
- POST /courses/{id}/publish, /archive and /restore, all checked against one table of allowed moves:
  - publish: Draft → Published
  - archive: Published → Archived
  - restore: Archived → Published
- Any other state-and-move pair returns 409. The message says the current state and what is allowed. The state doesn't change, and no log row is written. This includes archive on a draft, and publish on an archived course (that's what restore is for).
- A move that ends in Published needs at least one lesson; otherwise 409 explaining why. This covers publish and restore.
- A successful move writes one log row with the actor, from and to, and returns the course.
- Moves are instructor-only. Check the role before looking the course up, as the lesson endpoints already do, so a learner gets 403 even for a course that doesn't exist.
- Status changes only through moves. PUT /courses/{id} must not change it.

Locking
- Every move, every course edit and all four lesson changes take the same course-row lock before reading state. Otherwise publishing and removing the last lesson, or archiving and adding a lesson, could both succeed at once.
- The lesson service already has this lock; move it somewhere all of them can share.

Archived courses and the last lesson
- Archived courses are read-only. Editing the course, or adding, editing, reordering or removing a lesson, returns 409 ("This course is archived, so it can't be changed. Restore it first."). Nothing changes, and no log row is written.
- The last lesson of a published course can't be removed (409). That's allowed on a draft, and allowed when another lesson remains.

Comments
- POST /courses/{id}/comments with {"text": ...}. The text is trimmed and must be 1–2000 characters, otherwise 422.
- A comment is stored as an activity_log row, so the append-only trigger protects it too. The endpoint returns 201 with that row.
- Instructors can comment on any course, archived ones included. Archived means the content is read-only, not the discussion.
- Learners can comment too, because the brief says learners leave comments, so this endpoint must not give them 403. A learner gets the same 404 as GET /courses/{id}, whether the course doesn't exist or they just can't see it.

Reading the log
- GET /courses/{id}/activity, newest first. Each entry has action, details, created_at and actor {id, full_name}.

Decide with me before building (options plus a recommendation):
- Who can read the log.
  - Instructors only: a learner can post a comment and never see a reply. Learners get 403, with the role checked first.
  - Learners see only the comment entries, on courses they can see. They get the same 404 rule as GET /courses/{id}.
- Whether the feed needs paging now, and if so how.

Tests, beyond the obvious ones:

Moves
- All nine state × move pairs:
  - the three legal ones give 200, the new state and exactly one log row;
  - the six illegal ones give 409, leave the state unchanged and write no log row.
- Publish and restore with no lessons give 409. Set up the restore case directly in the database, since the app can't reach it.
- Learners get 403 on all three moves, including for a course id that doesn't exist.
- PUT /courses/{id} with a status field doesn't change the status.

Archived courses and the last lesson
- On an archived course, all five kinds of edit give 409, change nothing and log nothing, while a comment still works.
- Last-lesson rule: blocked on a published course, allowed on a draft, allowed when another lesson remains.

Locking
- For each of the eight kinds of change (three moves, the course edit, four lesson changes), capture the SQL with a before_cursor_execute listener on the test engine.
- Assert that SELECT ... FROM courses ... FOR UPDATE runs before any write.

Comments
- The text is trimmed.
- Blank text and 2001 characters give 422.
- A learner on a published course gets 201.
- A learner gets an identical 404 for a draft, an archived and a missing course.
- The trigger refuses to change or delete a comment row.

Feed
- Entries come newest first.
- Moves and comments appear, with actor names.
- The read rule I choose is enforced.

Check by hand: add a two-terminal lock check to your report, with exact PowerShell commands.
1. In terminal 1, open psql on the dev database (Docker, port 5433), run BEGIN, then SELECT ... FOR UPDATE on one course.
2. In terminal 2, send a publish request for that course. It should hang.
3. Run ROLLBACK in terminal 1. The request should finish.

Order: three changes. Finish and fully test each one, and hand it to me with its Summary, Description and file list. Then wait until I say it's committed before you start the next:
1. The moves and the shared lock.
2. The archived read-only rule and the last-lesson rule.
3. Comments and the activity feed.
Not in this step: enrolment, progress, the course list, the frontend.

When all three are committed, give me a short progress update: which of the ten goals changed status, the new endpoints, and the new test count for each test file.

Start here: show the plan and file list for all three changes, plus your options for the two decisions above, and wait for my go.
```

</details>

<details>
<summary>My answers to its plan</summary>

```text
Decision 1: (b). Instructors see everything; learners see only the comments, on courses they can see, with the same 404 rule as GET /courses/{id}.
Decision 2: (b). ?limit (default 50, max 100) and ?before=<entry id>.

Additions to change 3:
- Sort the feed by id, newest first, not by created_at, so the sort order and the cursor always agree.
- Load each page's actors together with the entries (selectinload or a join), not one query per entry. Using the SQL listener, test that the number of queries for a page doesn't grow with the number of entries.
- Add the author's role to ActorOut, so the frontend can mark instructor replies.

Add a change 4, after change 3, as its own commit: I'm reversing the step 2 choice to check activity_log.action only in code. This table is append-only, so a bad value could never be fixed, and after this step the list of actions is complete.
- Migration 0003 adds a CHECK listing every action.
- In the same migration, replace the index on course_id with one on (course_id, id), which matches the feed query.
- Update the comment on the action column to say why the database now checks it.
- Test that the database refuses an unknown action.
- Run 0003 down and up once on the dev database.

Everything else as planned. Go: start on change 1.
```

</details>

After its read-back:

```text
go
```

Then, after reviewing and committing each change: `committed` (three times).

### What I got

Four changes, each with its own report and commit text: the moves and a shared row lock; read-only archived courses and the last-lesson rule; comments and the feed; and migration 0003. 115 tests in total.

### What I corrected and checked

- I added change 4, reversing my step 2 choice: `activity_log.action` now has a database CHECK, because a bad value in an append-only table could never be fixed.
- The agent improved one of my tests. The test session already holds the users it creates, so code that loads each author separately would still pass a query count. It clears the session before measuring.
- Without being asked, it showed that each new kind of test can fail. Without the row lock, all eight lock tests failed. Without the archived guard, all five archived tests failed. With authors loaded one by one, a page took 13 queries instead of 5.
- It ran the two-terminal lock check: a publish request waited about 4 seconds for a lock held in psql, then finished.

## 7. The httpx2 swap

### Prompt

<details>
<summary>Full prompt</summary>

```text
next change in httpx2 swap like: ""
Switch the test client to httpx2, as its own change.
Starlette warns "Using httpx with starlette.testclient is deprecated; install httpx2". Its warning class inherits from UserWarning, so check with `python -m pytest -W error`, not `-W error::DeprecationWarning`.
1. Run `python -m pytest -W error` now; it should fail on that warning. Show me the line.
2. In backend/requirements.txt replace httpx==0.28.1 with httpx2==2.13.1 (confirm it's still the latest).
3. Check nothing else needs httpx or httpcore (`python -m pip show httpx httpcore`), uninstall both, reinstall the requirements.
4. Run `python -m pytest -W error` again: every test should pass with no warnings. If something else trips it, show me; don't hide it with a filter.
5. Tell me whether to make warnings-as-errors permanent (filterwarnings = error in pytest.ini), with a recommendation.
Then give me the Summary, Description and file list, and wait.
""
```

</details>

Then my answer to its two questions:

```text
Yes to both: add filterwarnings = error to pytest.ini, and pin truststore==0.10.4 in requirements.txt. Rerun pytest, then give me the final Summary, Description and file list.
```

### What I got

httpx2 2.13.1 in place, all 115 tests passing with warnings treated as errors, and truststore pinned to 0.10.4 because 0.10.5 was only two days old.

### What I corrected

Nothing. It recommended making warnings-as-errors permanent and proved the setting works with a test that only warns.

## 8. Drafting decisions.md

### Prompt

<details>
<summary>Full prompt</summary>

```text
next draft decisions ""Draft docs/decisions.md. Keep the template's format exactly: "## Decision N", then Chose / Rejected / Why, and a "**Later reversed:**" line on the reversed one. Plain, first person, short. Don't change any code. Use these decisions:

1. Login: a Bearer token in localStorage, 8-hour expiry, no refresh tokens. Rejected: httpOnly cookies (CSRF handling plus cross-site cookie setup between Vercel and Render) and refresh tokens (more moving parts than a 12-hour project needs). Trade-off: a token in localStorage is readable by any XSS on the page.
2. Accounts only from the seed script; no sign-up, and bulk enrolment never creates accounts. Rejected: self sign-up (the brief is an internal company tool) and creating accounts during bulk enrolment (a typo would silently create a person).
3. Any instructor can manage any course; instructor_id records the author. Rejected: course ownership (the brief says instructors build courses together, and ownership adds a permission layer nobody asked for).
4. Category is a fixed list (onboarding, compliance, skills) stored as text with a CHECK. Rejected: a categories table (no screen manages categories) and a Postgres ENUM type (harder to change in a migration).
5. Course states: one table of allowed moves (publish, archive, restore), one endpoint per move. Anything else gets 409. Publishing and restoring need at least one lesson; the last lesson of a published course can't be removed. Rejected: a PATCH that sets status directly (every caller would need to know the rules).
6. The activity log is append-only twice over: no update or delete code paths, plus a Postgres trigger that refuses UPDATE, DELETE and TRUNCATE. Comments are log rows too. Rejected: trusting the application alone (any script or admin with SQL access could rewrite history).
7. Every change to a course takes a row lock on the course (SELECT ... FOR UPDATE) first. Rejected: no locking (publishing and removing the last lesson at the same moment could both succeed) and optimistic version numbers (more code for a two-instructor team). Tested by capturing SQL, plus a manual two-terminal check.
8. Learners read only the comments in a course's log, not the edit history. Rejected: the whole log (it holds old values from when the course was still a draft) and instructors only (a learner could never read a reply).
9. Feed paging with ?limit and ?before=<id>, sorted by id. Rejected: page numbers (new entries shift pages, so entries repeat or get skipped).
10. REVERSED. Step 2 checked activity_log.action only in code, "because each step adds new actions". Reversed in step 3 with migration 0003, which adds a CHECK: in an append-only table a bad value can never be fixed, and the list of actions is now complete.""

Show me the draft before saving it.
```

</details>

### What I got

A draft of the ten decisions in the template's format.

### What I corrected

The agent corrected two claims in my notes. The brief never says instructors build courses "together"; it says the courses are "built by a couple of instructors". And the trigger doesn't stop everyone with SQL access, because the table's owner can drop it. What it guarantees is that rewriting history takes a deliberate step. I kept both corrections.

<!-- Add here anything you reworded in the draft before committing it. -->

## 9. Step 4: enrolment and progress

### Prompt

My nine decisions for step 4, the migration, the endpoints with their status codes, the tests I wanted, and the order of three commits. I asked for the plan and anything in my decisions it thought was wrong before any code.

<details>
<summary>Full prompt</summary>

```text
This message is step 4 of my build: enrolment and progress. Work through it in the order below and stop wherever it says to wait. docs/decisions.md (decisions 1–13) still stands; build on it. If your saved notes disagree with this message, this message wins.

How we work (unchanged): I make every design call; show a plan and the exact file list before changing anything; business rules only in services/, routers just validate and call; every permission and state rule enforced on the server; pytest tests for every rule, and the full suite (`python -m pytest`, warnings are errors) passes before you call a change done; never commit or push; after each change give me Summary, Description and file list, then wait until I say it's committed.

## My decisions for step 4 (already made)
1. Completing a lesson: the learner presses Mark complete on each lesson. The course state is worked out by the server from those, never set by hand.
2. Deleting a lesson that any learner has completed: refused with 409. The service checks first, and a RESTRICT foreign key from lesson_completions makes the database enforce it too. Lessons nobody completed are still hard-deleted.
3. A lesson added to a course a learner has already completed: they stay Completed (progress shows e.g. 5 of 6). The brief rejects any move other than Not started → In progress → Completed, so there is no going back.
4. Archived courses: enrolled learners keep read-only access. The course stays in My courses, marked archived; they can open it and its lessons, but can't complete anything new there (409). Learners who aren't enrolled still get 404.
5. Enrolment: published courses only.
6. Before enrolling, a learner sees a published course's title, description and lesson titles, but not lesson content.
7. Comments and the feed: learners must be enrolled. A learner who can see the course but isn't enrolled gets 403 ("Enrol in this course to join the discussion"); a course they can't see is still 404. Instructors are unchanged.
8. No unenrolling in this version.
9. Enrolments and completions are not written to activity_log: they are learner activity, not changes to the course.

## Database (migration 0004)
- enrollments: id; course_id → courses; user_id → users (a learner); status text with CHECK (not_started, in_progress, completed), default not_started; enrolled_by → users; enrolled_at default now(); started_at, completed_at, last_activity_at (nullable). UNIQUE (course_id, user_id). CHECKs tying status to times: completed exactly when completed_at is set; not_started exactly when started_at is empty. Indexes on (user_id) and (course_id, status).
- lesson_completions: id; enrollment_id → enrollments; lesson_id → lessons ON DELETE RESTRICT; completed_at default now(). UNIQUE (enrollment_id, lesson_id).
- Write the allowed values into the migration (not imported from app code). Run 0004 up, down, up on the dev database, and finish with alembic check.

## Endpoints and rules
- POST /courses/{id}/enroll: learners only (instructors 403, role checked before the lookup). The course must be published and visible (else 404). Already enrolled → 409. A race between two enrol requests must leave one row and give the loser 409 (catch the unique violation). Returns 201 with the enrolment.
- POST /courses/{id}/lessons/{lesson_id}/complete: enrolled learners only (not enrolled → 403, can't see course → 404, lesson not in this course → 404, archived course → 409). Completing a lesson twice changes nothing and returns 200.
  - One table of allowed progress moves (not_started → in_progress, in_progress → completed); any other move is a programming error.
  - The first completion moves Not started → In progress (sets started_at). Completing the last remaining lesson moves In progress → Completed (sets completed_at). A one-lesson course goes through both moves in one request. Every new completion sets last_activity_at.
  - Locking: take the enrolment row FOR UPDATE, and the course row FOR SHARE, so completions on the same course don't block each other but do wait for archiving or a lesson removal (which take FOR UPDATE).
- GET /me/courses: the learner's enrolled courses with course status (archived ones marked), progress state, lessons done and total, and the times.
- GET /courses/{id}: for a learner, lesson content only when enrolled; an enrolled learner also gets their own progress and completed lesson ids. Enrolled learners can open an archived course.
- GET /courses/{id}/progress: instructors only (learners 403, role first). Every enrolled learner with name, email, state, lessons done and total, and the times. Step 8's CSV will reuse this.
- Deleting a completed lesson: 409 with a clear message.
- Learners never see another learner's progress.

## Tests (beyond the obvious)
- Every progress move, including the one-lesson course; completing twice changes nothing; adding a lesson after completion leaves Completed.
- Enrol: published only; draft, archived and missing courses give identical 404s; twice → 409; instructors 403.
- The CHECKs: the database refuses a completed enrolment without completed_at, and a not_started one with started_at.
- Concurrency by constraint: two completions of the same lesson leave one row; two enrolments leave one row.
- Visibility: lesson content hidden before enrolling; enrolled learners can open an archived course, but completing there gives 409; not-enrolled learners get 404 for it.
- Comments and feed: enrolled learner allowed, visible-but-not-enrolled learner 403, invisible course 404.
- Deleting a completed lesson gives 409 and changes nothing; deleting an uncompleted one still works.
- A learner can't read another learner's progress anywhere.
- As before, show that the key tests can fail when the rule they guard is removed.

## Order: three changes, one commit each
1. Migration 0004, the models, POST /enroll and GET /me/courses.
2. Completing lessons: the progress moves, the locking, and the rule on deleting completed lessons.
3. Visibility: lesson content before enrolment, archived access for enrolled learners, enrolment for comments and the feed, and GET /courses/{id}/progress.
Then, as a fourth step with no code: draft decisions 14 onwards for docs/decisions.md from my nine decisions above, in the same format (titled, Chose / Rejected / Why), and a line for Decision 12 saying completed lessons can no longer be deleted. Show me the draft before saving.

Not in this step: bulk enrolment, the course list and search, the CSV, the frontend.

Check by hand: in your report for change 2, give me exact PowerShell commands to sign in as a learner, enrol in course 1, complete its lessons one by one, and see the state go Not started → In progress → Completed.

Start here: show the plan and file list for all three changes, and anything in my decisions you think is wrong or unclear, then wait for my go.
```

</details>

### What I got

A plan for the three changes, and five points it thought were wrong or unclear in my decisions.

### What the AI caught

- **A learner could get stuck at In progress.** If a course has lessons A, B and C, a learner has done A and B, and the instructor removes C (which nobody completed), the learner has finished everything but stays In progress forever, and after 14 days would show as an inactivity alert. I chose its fix: a removal moves such learners to Completed in the same transaction (Decision 16).
- **Enrolling could slip past an archive.** A learner enrolling at the same moment an instructor archives the course would end up enrolled in an archived course. Enrolment now takes the course row FOR SHARE, so the two wait for each other (Decision 18).
- **One more database check:** `last_activity_at` is set exactly when `started_at` is, which the inactivity alerts will rely on.
- Decisions 8 and 13 needed follow-up lines too, not only Decision 12.

## 10. Step 4: answers and reviews

### Prompts

My answers to its five points:

<details>
<summary>Answers</summary>

```text
My answers:
1. (a). When a lesson is removed, move every In-progress learner who has now finished all the remaining lessons to Completed, in the same transaction. completed_at is the removal time; leave last_activity_at unchanged, since the learner didn't do anything. Test it, including a learner who still has lessons left staying In progress.
2. Yes: enrolment takes the course row FOR SHARE, with a lock test.
3. Yes: enrolled learners can comment on and read the feed of an archived course.
4. (a): instructors get 403 on GET /me/courses, role checked first.
5. Yes: add the CHECK that last_activity_at is set exactly when started_at is.
Docs: yes, follow-up lines for Decisions 8, 12 and 13.
Your defaults are fine. Go: start on change 1.
```

</details>

After change 1, from my review of its report:

<details>
<summary>After change 1</summary>

```text
Committed.
Yes, add an index on lesson_completions.lesson_id in change 2's migration.

Two things for the next changes:
1. Change 2: until change 3 lets enrolled learners open archived courses, no learner can see an archived course, so completing a lesson there gives 404, not 409. Don't reorder the checks to make the 409 test pass, because that would tell learners who aren't enrolled that the course exists. Either move that test to change 3, or bring the visibility change into change 2.
2. Change 3: your default says a learner already enrolled in a course that is later archived gets 409 "already enrolled" if they enrol again. Today they get 404, and none of the planned tests checks it, so add one.

Start the change 2.
```

</details>

After change 2, once my own hand check had passed:

<details>
<summary>After change 2</summary>

```text
Committed.
The hand check printed Not started -> In progress -> Completed.
For the step 4 decisions draft later: note that finishing learners after a lesson removal runs two queries per In-progress learner, which is fine at this size.
Start change 3.
```

</details>

On the decision drafts:

<details>
<summary>On the decision drafts</summary>

```text
Good draft.
Three additions, then save:
1. Add an "Updated in step 4" line to Decision 7: enrolment and lesson completion take the course row FOR SHARE, then the enrolment row FOR UPDATE, the same course-first order as every other change, so completions don't block each other, they wait for an archive or a lesson removal, and no two requests can deadlock.
2. Decision 14, add to Why: the database also refuses an enrolment whose status and times disagree (CHECKs on completed_at, started_at and last_activity_at), so even a bug in the service can't store an impossible state.
3. Decision 22, Why: start with the brief. Goal 9 lists what the log records (creation, edits, publish and archive transitions, comments), and enrolments and completions aren't on that list. Keep the rest.
Skip the instructor 403 on My courses. Then save to docs/decisions.md.
```

</details>

### What I got

Three commits (enrolment and My courses; completing lessons; visibility and the progress list), each with its tests and a mutation check per rule, then Decisions 14 to 22.

### What I corrected

- In the plan, the test for "completing a lesson in an archived course gives 409" sat in change 2, but until change 3 a learner couldn't see an archived course at all, so that test could only pass by reordering the checks, which would tell learners who aren't enrolled that the course exists. The agent moved the test to change 3, with the visibility change that makes it reachable.
- The plan promised that re-enrolling in a course that was archived since gives 409, not 404, but no planned test checked it. I asked for one.

### Where the AI corrected me

My line for Decision 7 said enrolling locks the enrolment row too. It doesn't: it creates the row, so it only needs the shared course lock. The agent also narrowed my "no two requests can deadlock" to the claim the lock order actually guarantees. I kept both corrections.

## 11. Deploying the API (step 6a)

### Prompts

I asked for a readiness review and a plan before I created the Neon and Render accounts:

<details>
<summary>Readiness review and plan</summary>

```text
Step 6a: deploy the backend only. No frontend yet.

Goal: the API runs on Render's free tier, against a Postgres database on Neon's free tier, and passes a smoke test from my machine. I create the accounts and paste values into the dashboards myself; you get the code ready and tell me exactly what to do.

Facts to design around:
- Render free tier: no shell and no pre-deploy command, so migrations must run in the start command. The service sleeps after 15 minutes idle and takes about a minute to wake.
- Neon free tier: its compute also suspends when idle, so the first connection after a pause can fail or be slow.
- Settings come only from environment variables (app/core/config.py): DATABASE_URL, JWT_SECRET, JWT_EXPIRE_MINUTES, CORS_ORIGINS, SEED_PASSWORD. Neon's connection string must start with postgresql+psycopg:// for our driver.
- Python must be 3.12 on Render as well.
- I can't run the seed on Render, so I'll run python -m app.seed from my machine with DATABASE_URL pointing at Neon.

What I want from you:
1. A readiness review of the backend for this deploy. Check:
   - how Render will know to use Python 3.12;
   - the build and start commands, with the start command running alembic upgrade head before uvicorn and binding to 0.0.0.0:$PORT;
   - whether to use Neon's pooled or direct connection string, and why;
   - whether the engine needs pool_pre_ping or similar so a suspended Neon compute or a sleeping Render instance doesn't produce a 500 on the first request;
   - CORS for now (no frontend yet);
   - that /health doesn't touch the database, or whether it should.
2. A plan and file list before any code. Keep code changes minimal, and tell me which existing tests cover them.
3. After my go: the code changes, with tests passing (python -m pytest).
4. A step-by-step deploy guide I can follow:
   - Neon: create the project and database, and which connection string to copy;
   - running the migrations and seed from my machine against Neon first, so I see any failure locally;
   - Render: every field of the new Web Service form (root directory backend), every environment variable, and how to generate JWT_SECRET;
   - what usually breaks on a first deploy, and where I'd see it in Render's logs.
5. A PowerShell smoke test against the live URL:
   - /health;
   - an instructor login, then creating, adding a lesson to and publishing a course;
   - a learner login, then enrolling, completing a lesson and reading My courses;
   - a learner calling an instructor route gets 403.
   Show the output I should expect.
6. A short docs/deploy.md with the services, the environment variable names (no values), the commands, and the cold-start note.

Never put a real secret in any file. Don't run git commit or git push; I commit myself. Start with the readiness review and the plan, then wait for my go.
```

</details>

While it was planning, I deployed by hand, so I told it what I'd done and changed its plan:

<details>
<summary>Go, with changes</summary>

```text
Go, with changes. I deployed by hand while you were planning, and it's live at https://course-delivery-api.onrender.com (/health returns ok).
What I set: root directory backend; build "pip install -r requirements.txt"; start "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"; health check /health; env vars PYTHON_VERSION=3.12.7, DATABASE_URL (Neon Singapore, Postgres 17, database course_delivery, direct connection), JWT_SECRET. CORS_ORIGINS not set. Render region Singapore.
I seeded Neon from my machine: 7 demo accounts, no courses.
First-deploy problems, in order: no root directory (requirements.txt not found); Python 3.14 used by default; env vars not saved (DATABASE_URL not set). I also pasted the Neon connection string into a chat by mistake, so I reset the Neon password and updated Render.

Changes to your plan:
- Skip backend/.python-version. PYTHON_VERSION=3.12.7 already works, and one source of truth is safer.
- Keep backend/tests/test_health.py.
- The guide is no longer needed. Put what matters in docs/deploy.md instead: services, env var names only, commands, local migrate/seed against Neon, cold starts, the three first-deploy problems, and how to reset Neon before the final demo seed.
- Smoke test: as you planned, archiving its course at the end. Ask for the demo password with Read-Host, never from a file. Show the expected output.
- Draft a decision, in the titled format, for the deploy choices: migrations in the start command (no pre-deploy step on the free tier), the direct Neon connection, and the database-free /health. Show me before saving.
Don't run git commit or push.
```

</details>

### What I got

A readiness review. `pool_pre_ping` was already on, so no code change was needed; it recommended Neon's direct connection for migrations, and a `/health` that never touches the database. Then `docs/deploy.md`, a test that `/health` sends no SQL, Decision 23, and a PowerShell smoke test.

### What went wrong, and what I did

- **Three failed deploys.** The first had no root directory (`requirements.txt` not found), the second ran on Python 3.14, Render's default, and the third had no environment variables saved. I fixed each from Render's log.
- **I pasted the Neon connection string, with its password, into a chat** while seeding the database. I reset the password in Neon at once and updated Render, so the leaked one no longer works. Since then the seed instructions read the connection string from a hidden prompt.

### What the AI caught

The activity log is append-only, so anything the smoke test creates on the live database can never be deleted. The smoke test archives its course at the end, and `deploy.md` explains how to reset Neon before the final demo seed.

## 12. Step 5: course search

### Prompts

<details>
<summary>The search step</summary>

```text
Step 5: the course list with search, filters, sorting and pages (goal 6). Backend only.

The brief's exact rule:
"One list shows every course the viewer can see — published courses for learners, every course including drafts and archives for instructors — with a text search over titles and descriptions, filters for category, status and instructor, sorting by title, creation date or enrollment count, and pagination showing the total number of matches. All of this must happen on the server — do not load every course into the browser and filter there."

What I want: GET /courses with q, category, status, instructor_id, sort (title, created_at, enrollment_count), order (asc/desc), page, page_size. The response is items, total, page, page_size. Each item carries what a list row needs, including the enrolment count and the instructor's name.

Rules I already know:
- Learners see published courses only, enforced in the SQL, not after the query. That includes archived courses they're enrolled in: those live in My courses (Decision 17), not the catalogue.
- Every filter, the sort and the page happen in one database query (plus at most one for the total). A test proves the query count doesn't grow with the number of courses.
- Every sort has a tie-breaker (id), so pages never repeat or skip a course.
- Bad parameters (unknown sort, page 0, page_size above the maximum, unknown category or status) give 422.
- The search treats % and _ in the user's text as plain characters.

Before any code, give me options and trade-offs, and wait for my choices, on:
1. Search: ILIKE versus Postgres full-text search, and whether either needs an index at this size.
2. Enrolment count: counted on read (join or subquery) versus a stored counter on courses.
3. The total: a separate COUNT query versus a window function.
4. What a learner's status filter does: ignored, 422, or allowed only for "published".
5. Default sort and page size, and the maximum page size.
6. Anything in the rule above you think is wrong or unclear.

Then the plan and file list. Tests: every filter alone and combined, each sort in both directions with ties, page boundaries and total, learners never seeing a draft or archived course through any parameter, the 422s, the % and _ search, and the query count. Run the mutation checks as before. Show me the SQL generated for one call using every parameter, and tell me what slows down first at 100x the data.

Don't run git commit or push. Start with the options, then wait.
```

</details>

My choices from its options:

<details>
<summary>Choices</summary>

```text
1a, 2a, 3a, 4d, 5 your defaults, 6 yes to lower(title) then id, the join, and all your edge-case defaults.
One addition: each list item gets "enrolled": true/false for the viewer (an EXISTS subquery inside the page query, so still one query plus the count; always false for instructors). Add a test that it's true only for the viewer's own enrolments.
After the code, draft decisions for: ILIKE over full-text search, counting enrolments on read (including the deadlock a stored counter would cause with Decision 7's shared lock), and sorting by lower(title) because of collation. Show me the draft before saving.
Go.
```

</details>

After its report:

<details>
<summary>The title sort</summary>

```text
One change before saving: sort titles by lower(title) COLLATE "C", then id. lower() removes case, but the comparison still uses the database's collation, so spaces and punctuation could still order differently between Alpine and Neon. COLLATE "C" makes the order the same everywhere. Add one test with titles that differ only in a space or punctuation, so the order is pinned. Then fix Decision 26's Why to say this, and keep "My local Postgres (Alpine)" with its example.
Decisions 24 and 25 are right as written. Save all three after the change, and rerun the suite and the tie-breaker mutation.
```

</details>

### What I got

`GET /courses` with search, filters, sort and pages in one query plus one count, and 25 tests, each rule shown to fail when removed.

### What the AI caught

- **A stored enrolment counter would deadlock.** Enrolling holds the course row FOR SHARE (Decision 7), and updating a counter on that row needs a stronger lock, so two learners enrolling at once would each wait for the other. That's a better reason than effort to count on read (Decision 25).
- **Title order depends on the database's collation.** My local Alpine Postgres sorted `Apple, Zebra, apple, banana`.
- Its first query loaded every instructor's whole user row, password hash included, just to show a name. It changed the query to select only the name.
- It strengthened the query-count test before trusting it: with one shared instructor, loading instructors one by one would only have cost one extra query.

### What I corrected

The agent sorted titles by `lower(title)`. That removes case, but the comparison still uses the collation, so spaces and punctuation could still order differently on Neon. I asked for `lower(title) COLLATE "C"` (Decision 26).

### Where the AI corrected me

The test I asked for could never fail on my machine, because Alpine already sorts by bytes. The agent made the test also check that the SQL asks for `COLLATE "C"`, and showed it failing without it.

### My own mistake

I committed the follow-up change with my prompt to the agent as its commit message, and renamed it with `git commit --amend` and a force push.

## 13. Step 6b: the learner frontend on Vercel

### Prompts

<details>
<summary>The frontend step</summary>

```text
Step 6b: the first frontend, for learners, deployed to Vercel. The backend is live at https://course-delivery-api.onrender.com and its API is fixed: don't change backend code except CORS settings if needed.

Stack: React + Vite + Tailwind v4 + React Router v7, plain fetch, no component library, no state library, no TypeScript. Code lives in frontend/ with src/{api,pages,components}. All API calls go through src/api/ and read the base URL from VITE_API_URL. I'm on Windows with Application Control; check what Node and npm versions I have before anything else.

Pages for this step:
1. Login (email + password). Show the server's error message on failure. Show demo logins only as a hint text, no passwords in the code.
2. Course list (GET /courses): search box, category and sort controls, page controls with the total. Filters and the page live in the URL (useSearchParams), so a reload or a shared link keeps them. Debounce the search. Each row shows title, category, instructor, enrolment count, and "Enrolled" or an "Enrol" button (from the enrolled flag).
3. Course page (GET /courses/{id}): lessons in order. Before enrolling: titles only and an Enrol button. After enrolling: lesson content, "Mark complete" per lesson (done ones marked), and my progress (state, X of Y). An archived course I'm enrolled in shows read-only, with a note, and no Mark complete buttons.
4. My courses (GET /me/courses): each course with state and X of Y, archived ones labelled.
5. A nav bar with the user's name, role and Log out. Instructors can log in and browse the list; their own pages come next step, so show a short "instructor tools coming" note rather than hiding the gap.

Behaviour every page needs:
- Loading, empty and error states. Show the server's "detail" message on 4xx.
- A 401 anywhere logs the user out and returns to login.
- Render's free tier sleeps: if a request takes over ~3 seconds, show "Waking the server, this can take up to a minute".
- Buttons disable while their request runs, so double clicks don't send twice.
- The UI never decides permissions; it only reflects what the API returns.

Before any code, give me options and trade-offs, and wait for my choice, on:
1. Where the JWT lives: localStorage, sessionStorage, or memory only (and what each costs on reload and against XSS).
2. How to know the current user and role after login (decode the token, call GET /auth/me, or store the login response).
3. How Vercel serves client-side routes on reload (rewrites in vercel.json), and the exact CORS_ORIGINS value I set on Render.
4. Anything in this list you think is wrong, missing, or too much for one step.

Then the plan and file list. For checking: no frontend unit tests this step; instead give me a manual test checklist covering every page and state above, and tell me exactly how to run it locally against the live API and then on Vercel. Include the Vercel steps: project settings, root directory frontend, VITE_API_URL, and how to redeploy.

Don't run git commit or push. Start with the Node check and the options, then wait.
```

</details>

My choices from its options:

<details>
<summary>Choices</summary>

```text
1a, 2b, 3 as you described, 4 yes to four commits, hide Enrol for instructors (a), and all your additions.
Two more:
- Lesson content renders as plain text with line breaks kept (whitespace-pre-wrap), never as HTML.
- After each of the four commits' code, stop and give me its Summary, Description and file list, and wait for "committed" before starting the next.
At the end, draft decisions for: getting the user from /auth/me rather than the token, plain-text lesson content as the XSS defence for the localStorage token (Decision 1), and hiding instructor-only buttons as presentation while the server still decides. Show me before saving.
I've set CORS_ORIGINS=http://localhost:5173 on Render.
Go.
```

</details>

After commit 2's report:

<details>
<summary>The missing filters</summary>

```text
Not committed yet. One gap, and it's my mistake: goal 6 says "filters for category, status and instructor", and my spec only asked for category. Add both before commit 2:
- Status filter (All / Draft / Published / Archived), shown to instructors only. Learners only see published courses anyway, so for them it would do nothing.
- Instructor filter, for everyone. There's no endpoint listing instructors, so first add a small backend one as its own commit: GET /instructors, any signed-in user, returning id and full_name only (no emails), sorted by name. The names are already shown on course rows, so it reveals nothing new. Tests: both roles get it, no email in the response, 401 without a token.
Both filters live in the URL like the others, and changing either goes back to page 1. Add both to the browser checks, with a mutation check for each.
Order: the backend commit first (stop and give me its Summary, Description and files), then the updated commit 2.
Keep the .badge style in index.css. Add GET /instructors to the decisions you draft at the end of this step.
```

</details>

After commit 3, once I'd checked it by hand:

<details>
<summary>Commit 4 and the undo question</summary>

```text
Committed and pushed. Checked by hand: My courses, Mark complete through to Completed, the archived course, and the not-enrolled view all work. Start commit 4.

For the decisions draft at the end of this step, add one: completing a lesson is final, with no undo and no "mark incomplete". Goal 4 says any other move is rejected by the server; undoing would rewrite the completions the dashboard counts and break the inactivity alerts; and learners can already re-read any completed lesson, since content stays visible after completion.

As a possible future improvement (don't build it now), mention a personal "Revisit later" checklist: a checkbox per lesson, like a Markdown task list, that the learner can tick and untick freely. It is private to the learner, separate from Mark complete, and never changes progress, so it breaks no rule. It would need to look clearly different from the official "Done" badge, so nobody thinks Mark complete can be unticked.
```

</details>

### What I got

Before planning, the agent built a throwaway app with the exact versions it meant to pin, to prove Application Control on my machine wouldn't block the frontend tools. Then four commits (sign-in, the course list, the course page and My courses, the Vercel setup), checked in a real browser for both roles, with each key rule shown to fail when broken, and Decisions 27 to 31. It's live at https://course-delivery-app.vercel.app.

### What I corrected

- **My spec missed two filters.** Goal 6 asks for filters on category, status and instructor; I had only asked for category. The agent flagged it in its report. The instructor filter needed a list of instructors, so `GET /instructors` went in as its own backend commit (Decision 30).
- **I asked for an undo on "Mark complete".** Thinking it through, goal 4 rejects any backward move, undoing would rewrite the completions the dashboard counts, and learners can already re-read a completed lesson. I recorded it as Decision 31 instead, with a private "Revisit later" checklist as a possible future improvement.

### What the AI caught

- Its line-break check passed for the wrong reason: it found the lesson text by the very class being tested. It fixed the check and showed it failing when line breaks were dropped. That's the third time an agent test was strengthened before being trusted.
- On the CORS setting, it recommended allowing exact origins only, so Vercel's preview deployments can't call the API (the update to Decision 23).

### My own mistakes

- One commit took the course-list files along with the `GET /instructors` change, because GitHub Desktop ticks every changed file. I undid it with `git reset HEAD~1` and redid it as two commits.
- The agent stopped my own dev server once while freeing its ports. It now stops only the processes on its own ports.

## 14. Writing schema.md

### Prompt

<details>
<summary>Full prompt</summary>

```text
Docs only, no code changes: fill in docs/schema.md. It's still the template; answer each of its five questions in plain words, in my voice, accurate to the migrations 0001-0005 and the models as they are now:
1. Table by table: columns and types (users, courses, lessons, activity_log, enrollments, lesson_completions).
2. Relationships: one-to-many (course -> lessons, course -> activity_log, enrollment -> lesson_completions) and many-to-many (users <-> courses through enrollments).
3. Which rules the database enforces (unique constraints, CHECKs, RESTRICT foreign key, the append-only trigger, the action CHECK) and which the services enforce (roles, state moves, visibility), and why the line is drawn there. Point to the decision numbers.
4. What is deliberately denormalised, if anything (say so honestly if nothing is; enrolment counts are computed on read, Decision 25).
5. What breaks first at 100x: the enrolment-count sort, the ILIKE scans, deep OFFSET pages, and the fix for each.
Keep it short and readable, with one small table per database table. Leave a line saying the alert dismissals table arrives with goal 10. Show me the draft before saving.
```

</details>

### What I got

A draft of all five answers. I had it checked line by line against the five migrations before saving: every column, type, constraint and index matched. For question 4 it didn't write "nothing denormalised"; it named the log copying titles and old values, and the enrolment's start and last-activity times, and explained why neither can drift.