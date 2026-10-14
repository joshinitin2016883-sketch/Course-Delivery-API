# Decisions

## Decision 1: Sign-in tokens

- **Chose:** Sign-in returns a Bearer token (a JWT) that the frontend keeps in localStorage and sends in the Authorization header. It expires after 8 hours, and there are no refresh tokens.
- **Rejected:** httpOnly cookies, and refresh tokens.
- **Why:** The frontend (Vercel) and the API (Render) are on different sites, so cookies would mean cross-site cookie settings plus CSRF protection. Refresh tokens are more moving parts than a 12-hour project needs; after 8 hours you sign in again. The trade-off I accepted: a token in localStorage can be read by any XSS on the page.
- **Updated in step 6b:** The frontend's defence against that XSS is Decision 28: lesson content, like every other text from the server, is shown as plain text and never as HTML.

## Decision 2: Where accounts come from

- **Chose:** Accounts come only from the seed script. There is no sign-up, and bulk enrolment never creates accounts.
- **Rejected:** Self sign-up, and creating accounts during bulk enrolment.
- **Why:** This is an internal company tool, so accounts should come from the company, not from people signing themselves up. If bulk enrolment created accounts, one typo in a pasted list would silently create an account for someone who doesn't exist; instead, the address is reported as unknown.

## Decision 3: Who can manage a course

- **Chose:** Any instructor can manage any course. `instructor_id` only records who created it.
- **Rejected:** Course ownership, where only a course's author could change it.
- **Why:** The brief has a couple of instructors building the courses and never ties a course to one of them. Ownership would add a permission layer nobody asked for, and the activity log already records which instructor made each change.

## Decision 4: Course categories

- **Chose:** A fixed list of categories (onboarding, compliance, skills), stored as text with a CHECK constraint.
- **Rejected:** A categories table, and a Postgres ENUM type.
- **Why:** The three come from the brief's scenario, and no screen manages categories, so a table would only add a join. A Postgres ENUM is harder to change in a migration than a CHECK. Adding a category means a code change and a small migration, which is fine for a list this stable.

## Decision 5: Course states

- **Chose:** One table of allowed moves (publish: Draft → Published, archive: Published → Archived, restore: Archived → Published) and one endpoint per move. Any other move gets a 409. Publishing and restoring need at least one lesson, and the last lesson of a published course can't be removed.
- **Rejected:** A PATCH that sets the status directly.
- **Why:** With a status PATCH, every caller would need to know the rules. With one endpoint per move, the rules live in one place on the server, and each refusal says why: the current status, and the move allowed from it.

## Decision 6: An append-only activity log

- **Chose:** The activity log is append-only twice over. No code updates or deletes log rows, and a Postgres trigger refuses UPDATE, DELETE and TRUNCATE on the table. Comments are log rows too, so they get the same protection.
- **Rejected:** Trusting the application alone.
- **Why:** The brief says nothing in the log can be edited or deleted, "including by the instructor". If only the application enforced that, any script or person with SQL access could quietly rewrite history. With the trigger, they would first have to remove it on purpose.

## Decision 7: Locking the course row

- **Chose:** Every change to a course (the three moves, editing the course, and adding, editing, reordering or removing a lesson) first locks the course's row with `SELECT ... FOR UPDATE`.
- **Rejected:** No locking, and optimistic version numbers.
- **Why:** Without a lock, publishing a course and removing its last lesson at the same moment could both succeed, leaving a published course with no lessons. Version numbers would mean more code and a retry path, for a couple of instructors. A test captures the SQL each change sends and checks the lock comes first, and I also checked it by hand with two terminals.
- **Updated in step 4:** Enrolling and completing a lesson take the course row `FOR SHARE` instead, and completing a lesson then locks the learner's enrolment row `FOR UPDATE`. That's the same course-first order as every other change, so completions don't block each other, they wait for an archive or a lesson removal (which waits for them in turn), and these requests can't deadlock each other.

## Decision 8: What learners see in the log

- **Chose:** Learners see only the comments in a course's log, and only on courses they can see. Instructors see everything.
- **Rejected:** Showing learners the whole log, and keeping the log instructors-only.
- **Why:** The whole log holds old values from when the course was still a draft, which learners were never meant to see. Instructors-only would mean a learner could post a question and never read the reply.
- **Updated in step 4:** A learner now has to be enrolled to read the comments or comment (Decision 20).

## Decision 9: Paging the feed

- **Chose:** The feed pages with `?limit` (default 50, at most 100) and `?before=<entry id>`, sorted by id, newest first.
- **Rejected:** Page numbers.
- **Why:** New entries arrive at the top, so with page numbers every page shifts, and an entry can repeat or be skipped. Sorting by id means the order and the cursor always agree.

## Decision 10: Checking log actions in the database (reversed)

- **Chose:** In step 2, check `activity_log.action` only in code.
- **Rejected:** A database CHECK listing the allowed actions.
- **Why:** Each build step was adding new actions, and a CHECK would have needed a new migration every time.
- **Later reversed:** In step 3, migration 0003 added the CHECK. The log is append-only, so a row with a bad action could never be fixed, and by then the list of actions was complete.

## Decision 11: Reordering lessons

- **Chose:** Instructors can reorder all the lessons in a course with a single request. The server checks that the list contains exactly the lessons belonging to that course, updates their positions in one transaction, and records one activity log entry.
- **Rejected:** Sending a separate request to move each lesson up or down.
- **Why:** Moving a lesson across a long list would require multiple requests and create unnecessary log entries. A single request supports both drag-and-drop and up/down buttons. If the course changes before the reorder is submitted, the server returns a 409 error instead of guessing the correct order.

## Decision 12: Removing lessons

- **Chose:** When an instructor removes a lesson, it is permanently deleted from the database. However, its title and position are saved in the activity log so the history remains clear.
- **Rejected:** Keeping the lesson in the database with a flag marking it as removed.
- **Why:** At this stage, nothing else depends on a lesson, so permanently deleting it is the simplest approach. The activity log stores the lesson details separately, making it possible to see what was removed later. I'll revisit this in step 4, because deleting a lesson that learners have already completed will need additional rules.
- **Updated in step 4:** A lesson that any learner has completed can no longer be deleted (Decision 15). Lessons nobody has completed are still deleted outright.

## Decision 13: Comments on archived courses

- **Chose:** Instructors can continue adding comments to archived courses.
- **Rejected:** Making archived courses completely read-only, including their comments.
- **Why:** Archiving a course should prevent changes to its content without stopping further discussion. For example, an instructor might want to explain why a course was retired. For now, only instructors can comment on archived courses because learners cannot access them. I'll decide in step 4 whether enrolled learners should keep access to archived courses.
- **Updated in step 4:** Enrolled learners keep read-only access to archived courses, so they can comment there too (Decision 17).

## Decision 14: Completing a lesson

- **Chose:** A learner presses "Mark complete" on each lesson. The server works out their state for the course (Not started, In progress, Completed) from those completions, through one table of allowed moves. Nobody sets it by hand.
- **Rejected:** Counting a lesson as done when it's opened, and letting anyone set a learner's status directly.
- **Why:** The brief's complaint is not being able to tell who finished a course from who "merely opened it once", so opening a lesson can't count. A status anyone can set is the self-reported spreadsheet again. Because the state comes from completions, the only moves that can happen are Not started → In progress → Completed, which is all the brief allows. The database also refuses an enrolment whose status and times disagree (CHECKs tying the status to started_at, completed_at and last_activity_at), so even a bug in the service can't store an impossible state.

## Decision 15: Removing a lesson that learners have completed

- **Chose:** Refuse it with a 409. The service checks first, and a RESTRICT foreign key from lesson_completions makes the database refuse it too. Lessons nobody has completed are still deleted outright, and an index on lesson_completions.lesson_id keeps both checks fast.
- **Rejected:** Deleting the learners' completions along with the lesson, and keeping removed lessons with a "removed" flag.
- **Why:** A completion is a record of what a learner did. Deleting it would quietly rewrite their history. A flag would have to be filtered out of every query. Instructors can still edit a lesson that has been completed.

## Decision 16: Progress when lessons change

- **Chose:** Adding a lesson never moves a learner back: someone who completed the course stays Completed and sees, say, 5 of 6. Removing a lesson moves every In-progress learner who has now done all the remaining lessons to Completed, in the same transaction, with completed_at set to the removal time and last_activity_at left alone.
- **Rejected:** Recomputing each learner's state from scratch whenever the lessons change, and leaving learners In progress when there's nothing left for them to do.
- **Why:** The brief only allows Not started → In progress → Completed, and recomputing could move a Completed learner back. Leaving finished learners In progress would strand them with nothing to complete, and they'd show up as inactive after 14 days. Finishing them after a removal runs two queries per In-progress learner, which is fine at this size; with many more learners it would become one grouped query.

## Decision 17: Archived courses and enrolled learners

- **Chose:** Enrolled learners keep read-only access to an archived course. It stays in My courses, marked as archived, and they can open it, read its lessons, comment and read the comments. Completing a lesson there gets a 409. Learners who aren't enrolled get the same 404 as for a course that doesn't exist.
- **Rejected:** Hiding archived courses from everyone, and letting learners keep making progress in them.
- **Why:** The brief says archiving removes a course from the catalogue without deleting any learner's enrolment history, so learners should still see their own record. Archived means retired, though, so their progress there is frozen.

## Decision 18: Enrolling

- **Chose:** Learners enrol themselves, in published courses only (instructors will enrol learners through bulk enrolment, later). Enrolling takes a shared lock on the course row, so an archive can't slip in at the same moment. The unique constraint on course and learner is the "already enrolled" check.
- **Rejected:** Enrolling in drafts or archived courses, and checking for an existing enrolment in code before inserting.
- **Why:** A draft isn't finished and an archived course is retired, so neither should take new learners. A check in code can't stop two requests that arrive together. The database constraint can, and both cases end in the same 409.

## Decision 19: What learners see before enrolling

- **Chose:** Before enrolling, a learner sees a published course's title, description and lesson titles, but not the lessons' content.
- **Rejected:** Showing everything, and showing only the title and description.
- **Why:** The lesson titles are enough to decide whether to take a course. The content is for enrolled learners, whose progress is tracked. If everyone could read it, people could work through a course without it ever showing up in anyone's records.

## Decision 20: Joining a course's discussion

- **Chose:** A learner has to be enrolled to comment or read the comments. A learner who can see the course but isn't enrolled gets a 403 ("Enrol in this course to join the discussion"). A course they can't see is still a 404. Instructors can join any course's discussion.
- **Rejected:** Letting any learner who can see the course join in.
- **Why:** The discussion belongs to the people taking the course. Checking visibility before enrolment means the 403 never reveals a course a learner isn't allowed to know about.

## Decision 21: Unenrolling

- **Chose:** No unenrolling in this version.
- **Rejected:** An endpoint that removes an enrolment.
- **Why:** The brief doesn't ask for it, and it would need rules for what happens to the learner's completions and history, which the brief says must be kept.

## Decision 22: What goes in the activity log

- **Chose:** Enrolments and completions aren't written to the activity log. They live in their own tables, with their times.
- **Rejected:** Logging every enrolment and completion.
- **Why:** The brief's goal 9 lists what the log records: when the course was created, every edit, every publish or archive transition, and comments. Enrolments and completions aren't on that list. They're learner activity rather than changes to the course, and logging them would bury the course's history under progress entries. The enrollments and lesson_completions tables already record who did what and when.

## Decision 23: Deploying the API

- **Chose:** Run the migrations in Render's start command (`python -m alembic upgrade head && python -m uvicorn ...`), connect to Neon with its direct connection string, and keep `/health` free of database queries.
- **Rejected:** A pre-deploy step for migrations, Neon's pooled connection string, and a health check that queries the database.
- **Why:** Render's free tier has no shell and no pre-deploy command, so the start command is the only place the app can migrate itself. A failed migration stops uvicorn from starting, so a broken deploy fails loudly. The migration reruns on every wake from sleep, but at the latest version it does nothing, and with a single instance there's no race. Neon recommends a direct connection for migrations, and the app is one long-running process with its own small pool, so its connection pooler adds nothing; one URL serves both. Render calls `/health` repeatedly, and a database query there would keep waking Neon, which suspends after 5 idle minutes on the free plan, and use up its compute hours. A cold Neon could also fail a check and get the service restarted. The smoke test's logins prove the database works instead.
- **Updated in step 6b:** `CORS_ORIGINS` lists exact origins only: the Vercel domain and `http://localhost:5173`. Vercel's preview deployments each get a domain of their own, so they are deliberately not allowed to call the API. Allowing them would take a wildcard that any site on vercel.app could use, not just this project.

## Decision 24: Searching courses

- **Chose:** A case-insensitive substring search (`ILIKE '%text%'`) over titles and descriptions, with `\`, `%` and `_` in the user's text escaped so they match themselves. No index for now.
- **Rejected:** Postgres full-text search.
- **Why:** Substring matching finds part of a word ("comp" finds "Compliance") and is easy to predict and explain. Full-text search handles word forms and ranking, but it misses partial words, drops English stop words, and needs a stored search column and an index before it's worth using. At this size Postgres reads the whole courses table in microseconds. With far more courses, a pg_trgm index would speed up exactly this ILIKE without changing the query.

## Decision 25: Counting enrolments when the list is read

- **Chose:** Count each course's enrolments inside the list query (a subquery on enrollments), counting every enrolment whatever its state.
- **Rejected:** A stored enrollment_count column on courses, updated with each enrolment.
- **Why:** A count worked out on read is always right, needs no migration, and nothing has to remember to keep it up to date. A stored counter would also clash with Decision 7: enrolling holds the course row `FOR SHARE`, and updating a counter on that row needs a stronger lock, so two learners enrolling in the same course at once would each wait for the other's shared lock, which is a deadlock. The cost is that sorting by enrolment count counts every matching course before choosing a page. That's the first thing to slow down at 100x the data, and the point to revisit, for example with a separate counts table that doesn't touch the course row.

## Decision 26: Sorting titles by lower(title) COLLATE "C"

- **Chose:** Sort titles by `lower(title) COLLATE "C"`, then by id.
- **Rejected:** Sorting by the plain `title` column, or by `lower(title)` under the database's own collation.
- **Why:** How text sorts depends on the database's collation, which can differ between environments. My local Postgres (Alpine) puts capitals first: "Apple, Zebra, apple, banana". `lower()` removes the difference in case, but the comparison would still use the database's collation, so titles that differ only in a space or punctuation could still come out in a different order on Alpine and on Neon. `COLLATE "C"` compares the lower-cased titles byte by byte, which gives the same order on every database, and the id tie-breaker keeps otherwise identical titles in a fixed order, so pages never repeat or skip a course. The cost is that accented letters sort after "z".

## Decision 27: Who is signed in comes from GET /auth/me

- **Chose:** The frontend learns who is signed in, with their name and role, from `GET /auth/me`: right after signing in, and again on every page load when a token is saved. It never reads anything out of the token itself.
- **Rejected:** Decoding the JWT in the browser, and adding the name and role to the token.
- **Why:** The token holds only the user's id and its expiry, and the server reads the role from the database on every request. Asking `/auth/me` means the page always shows the role the server enforces, even if it changed after the token was issued. The browser can't check a token's signature, so a decoded token could also be stale or edited, which would fool the page though never the server. The request on load also tests the saved token: an expired one sends you to sign in straight away, not after your first click.

## Decision 28: Lesson content is plain text

- **Chose:** Lesson content is shown as plain text with its line breaks kept (`white-space: pre-wrap`), and so is every other text from the server. Nothing in the frontend uses `dangerouslySetInnerHTML`, so HTML typed into a lesson shows as typed.
- **Rejected:** Rendering lessons as HTML or as Markdown.
- **Why:** This is the defence Decision 1 relies on. The token sits in localStorage, where any script running on the page can read it, and lesson content is the largest text that one person writes and many other people's browsers display. React escapes text, so as long as nothing is turned into HTML, a script in a lesson can't run. HTML or Markdown would need a sanitiser that is right every time. Plain lessons only need line breaks, and those are kept. If rich text is wanted later, it should come with a well-tested sanitiser and a Content-Security-Policy.

## Decision 29: Hiding buttons is presentation; the server decides

- **Chose:** Each page hides what the signed-in person can't use: Enrol and My courses for instructors, the status filter for learners, and Mark complete before enrolling or on an archived course. The API still enforces every one of these rules, and when it refuses, the page shows the server's own message.
- **Rejected:** Showing every button and letting the server refuse, and treating the hidden buttons as the protection.
- **Why:** Hiding what you can't use keeps each page clear. But anyone can call the API without the page, so the page can't be where the rules live. An instructor who enrols anyway gets a 403, completing a lesson before enrolling gets a 403, completing one in an archived course gets a 409, and a learner is never sent a draft. A page that's out of date, say a course archived while it's open, still ends with a clear answer: the server refuses, and the page shows why.

## Decision 30: Listing instructors for the filter

- **Chose:** `GET /instructors`, for any signed-in user, returning each instructor's id and full name (never the email), sorted like titles: `lower(full_name) COLLATE "C"`, then id. The course list's instructor filter offers these names.
- **Rejected:** Taking the names from the courses on the current page, and a general `GET /users`.
- **Why:** Goal 6 asks for a filter by instructor. The page holds only one page of courses, so its names would miss instructors whose courses are elsewhere in the list. A general users endpoint would expose learners. The instructors' names are already on every course row, so listing them reveals nothing new, and the query selects only the id and name, so the email can't leak. Sorting follows Decision 26, so names come out in the same order on every database.

## Decision 31: Completing a lesson is final

- **Chose:** A completed lesson stays completed. There's no undo and no "mark incomplete".
- **Rejected:** An undo button, and a "mark incomplete" action.
- **Why:** Goal 4 allows only Not Started → In Progress → Completed and says the server rejects any other move. Undoing would also rewrite the completions the dashboard counts (completions this month, and the eight-week chart), and break the inactivity alerts, which depend on when a learner last made progress. Learners lose nothing: a completed lesson's content stays visible, so they can re-read it whenever they like.
- **Possible future improvement (not built):** A personal "Revisit later" checklist: a checkbox per lesson, like a Markdown task list, that the learner can tick and untick freely. It would be private to the learner, separate from Mark complete, and would never change progress, so it breaks no rule. It would need to look clearly different from the official "Done" badge, so nobody thinks Mark complete can be unticked.
