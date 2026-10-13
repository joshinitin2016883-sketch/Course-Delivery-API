# Decisions

## Decision 1

- **Chose:** Sign-in returns a Bearer token (a JWT) that the frontend keeps in localStorage and sends in the Authorization header. It expires after 8 hours, and there are no refresh tokens.
- **Rejected:** httpOnly cookies, and refresh tokens.
- **Why:** The frontend (Vercel) and the API (Render) are on different sites, so cookies would mean cross-site cookie settings plus CSRF protection. Refresh tokens are more moving parts than a 12-hour project needs; after 8 hours you sign in again. The trade-off I accepted: a token in localStorage can be read by any XSS on the page.

## Decision 2

- **Chose:** Accounts come only from the seed script. There is no sign-up, and bulk enrolment never creates accounts.
- **Rejected:** Self sign-up, and creating accounts during bulk enrolment.
- **Why:** This is an internal company tool, so accounts should come from the company, not from people signing themselves up. If bulk enrolment created accounts, one typo in a pasted list would silently create an account for someone who doesn't exist; instead, the address is reported as unknown.

## Decision 3

- **Chose:** Any instructor can manage any course. `instructor_id` only records who created it.
- **Rejected:** Course ownership, where only a course's author could change it.
- **Why:** The brief has a couple of instructors building the courses and never ties a course to one of them. Ownership would add a permission layer nobody asked for, and the activity log already records which instructor made each change.

## Decision 4

- **Chose:** A fixed list of categories (onboarding, compliance, skills), stored as text with a CHECK constraint.
- **Rejected:** A categories table, and a Postgres ENUM type.
- **Why:** The three come from the brief's scenario, and no screen manages categories, so a table would only add a join. A Postgres ENUM is harder to change in a migration than a CHECK. Adding a category means a code change and a small migration, which is fine for a list this stable.

## Decision 5

- **Chose:** One table of allowed moves (publish: Draft → Published, archive: Published → Archived, restore: Archived → Published) and one endpoint per move. Any other move gets a 409. Publishing and restoring need at least one lesson, and the last lesson of a published course can't be removed.
- **Rejected:** A PATCH that sets the status directly.
- **Why:** With a status PATCH, every caller would need to know the rules. With one endpoint per move, the rules live in one place on the server, and each refusal says why: the current status, and the move allowed from it.

## Decision 6

- **Chose:** The activity log is append-only twice over. No code updates or deletes log rows, and a Postgres trigger refuses UPDATE, DELETE and TRUNCATE on the table. Comments are log rows too, so they get the same protection.
- **Rejected:** Trusting the application alone.
- **Why:** The brief says nothing in the log can be edited or deleted, "including by the instructor". If only the application enforced that, any script or person with SQL access could quietly rewrite history. With the trigger, they would first have to remove it on purpose.

## Decision 7

- **Chose:** Every change to a course (the three moves, editing the course, and adding, editing, reordering or removing a lesson) first locks the course's row with `SELECT ... FOR UPDATE`.
- **Rejected:** No locking, and optimistic version numbers.
- **Why:** Without a lock, publishing a course and removing its last lesson at the same moment could both succeed, leaving a published course with no lessons. Version numbers would mean more code and a retry path, for a couple of instructors. A test captures the SQL each change sends and checks the lock comes first, and I also checked it by hand with two terminals.

## Decision 8

- **Chose:** Learners see only the comments in a course's log, and only on courses they can see. Instructors see everything.
- **Rejected:** Showing learners the whole log, and keeping the log instructors-only.
- **Why:** The whole log holds old values from when the course was still a draft, which learners were never meant to see. Instructors-only would mean a learner could post a question and never read the reply.

## Decision 9

- **Chose:** The feed pages with `?limit` (default 50, at most 100) and `?before=<entry id>`, sorted by id, newest first.
- **Rejected:** Page numbers.
- **Why:** New entries arrive at the top, so with page numbers every page shifts, and an entry can repeat or be skipped. Sorting by id means the order and the cursor always agree.

## Decision 10

- **Chose:** In step 2, check `activity_log.action` only in code.
- **Rejected:** A database CHECK listing the allowed actions.
- **Why:** Each build step was adding new actions, and a CHECK would have needed a new migration every time.
- **Later reversed:** In step 3, migration 0003 added the CHECK. The log is append-only, so a row with a bad action could never be fixed, and by then the list of actions was complete.
