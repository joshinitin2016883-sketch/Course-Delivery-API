
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
