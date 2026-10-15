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
- **Updated in step 7:** The page reorders with up/down buttons and sends the new order once, on Save order (Decision 34). A 409 for an outdated order is shown with a Reload button.

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
- **Updated in step 8:** Instructors now enrol learners in bulk (Decision 42). It keeps the same rules: published courses only, the same shared lock, and the unique constraint as the "already enrolled" check.

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
- **Updated in step 8:** Bulk enrolment by an instructor isn't logged either. `enrollments.enrolled_by` records which instructor enrolled each learner, and `enrolled_at` records when.

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
- **Updated in step 7:** The same goes for the instructor tools. The manage section, the lesson tools, the learners table, New course and Courses I created are shown to instructors only, and the comment box only to people who can join the discussion. Inputs carry the API's length limits as maxLength, which only stops typing past them; the server still checks every value.
- **Updated in step 8:** Enrol learners and Download CSV are shown to instructors only; the server refuses learners with 403.

## Decision 30: Listing instructors for the filter

- **Chose:** `GET /instructors`, for any signed-in user, returning each instructor's id and full name (never the email), sorted like titles: `lower(full_name) COLLATE "C"`, then id. The course list's instructor filter offers these names.
- **Rejected:** Taking the names from the courses on the current page, and a general `GET /users`.
- **Why:** Goal 6 asks for a filter by instructor. The page holds only one page of courses, so its names would miss instructors whose courses are elsewhere in the list. A general users endpoint would expose learners. The instructors' names are already on every course row, so listing them reveals nothing new, and the query selects only the id and name, so the email can't leak. Sorting follows Decision 26, so names come out in the same order on every database.

## Decision 31: Completing a lesson is final

- **Chose:** A completed lesson stays completed. There's no undo and no "mark incomplete".
- **Rejected:** An undo button, and a "mark incomplete" action.
- **Why:** Goal 4 allows only Not Started → In Progress → Completed and says the server rejects any other move. Undoing would also rewrite the completions the dashboard counts (completions this month, and the eight-week chart), and break the inactivity alerts, which depend on when a learner last made progress. Learners lose nothing: a completed lesson's content stays visible, so they can re-read it whenever they like.
- **Possible future improvement (not built):** A personal "Revisit later" checklist: a checkbox per lesson, like a Markdown task list, that the learner can tick and untick freely. It would be private to the learner, separate from Mark complete, and would never change progress, so it breaks no rule. It would need to look clearly different from the official "Done" badge, so nobody thinks Mark complete can be unticked.

## Decision 32: Instructor tools on the course page

- **Chose:** The instructor's tools are sections of the existing course page, shown by role: managing the course, its lessons, the enrolled learners, and the activity feed. Creating a course has its own small page, `/courses/new`.
- **Rejected:** Separate `/manage` routes for instructors.
- **Why:** One address per course works for both roles, so every link (the course list, My courses) leads to the same page. Instructors see what learners see, plus their tools, and the feed is written once. Showing the sections by role is presentation (Decision 29): the API refuses every one of these tools to learners.

## Decision 33: "Courses I created" is a filter, not ownership

- **Chose:** Instructors have "Courses I created" in the nav: the course list filtered to `instructor_id` = their id, in the URL like every other filter. It uses the existing `GET /courses`.
- **Rejected:** Calling it "My teaching", and a separate endpoint or flag for an instructor's own courses.
- **Why:** `instructor_id` only records who created a course, and any instructor can manage any course (Decision 3). "My teaching" would suggest the other courses aren't theirs to manage. As a filter, the view can be bookmarked and combines with the search and the other filters.

## Decision 34: Reordering lessons with up/down buttons

- **Chose:** Each lesson has ↑ and ↓ buttons. Moves only change the page until Save order sends the whole order in one request, which writes one log entry; Cancel puts the saved order back. Editing, removing and adding wait until the new order is saved or cancelled.
- **Rejected:** Drag and drop, either native or with a library, and saving after every click.
- **Why:** Buttons work with the keyboard and screen readers as they are ("Move "Getting started" up"), and a test only has to click them. Native drag and drop has no keyboard support and is unreliable on touch screens; a library such as dnd-kit would fix that at the cost of a dependency to explain. Saving after every click would write a log entry per click, which Decision 11 set out to avoid. Drag and drop could be added later on top of the same request.

## Decision 35: Asking before removing a lesson or archiving

- **Chose:** Remove lesson and Archive ask once more on the page itself, for example "Remove lesson 2, "Going further"? This can't be undone." with Remove and Cancel, through one shared ConfirmButton. Cancel takes the focus. Publish and Restore act straight away.
- **Rejected:** No confirmation, and the browser's `confirm()` dialog.
- **Why:** Removing a lesson deletes it for good (Decision 12), and archiving takes a course out of the catalogue and freezes learners' progress, so a mis-click costs something. `confirm()` is unstyled, browsers let people switch such dialogs off, and tests have to handle a dialog; a step on the page is just plain buttons. Restore undoes an archive, and Publish is the expected next step for a finished draft, so asking first there would only slow people down.

## Decision 36: Only the allowed move, and every refusal shown

- **Chose:** The manage section offers only the move allowed from the current status: Publish on a draft, Archive on a published course, Restore on an archived one. A button the server might still refuse stays visible, so its reason can show. That covers Publish on a draft with no lessons, and Remove on the last lesson of a published course or on a lesson learners have completed. An archived course hides its editing and lesson tools behind a note: "This course is archived and read-only. Restore it to make changes."
- **Rejected:** Showing all three moves all the time, and hiding or disabling a button whenever the page guesses the server would refuse.
- **Why:** A move that's never allowed from the current status only invites a refusal. But the brief wants the server's explanation when someone tries to publish an empty course. And the page can't always know what the server will say, because another instructor may have archived or published the course since it loaded. So the page offers what's possible, the server decides, and its message is shown whenever it refuses (Decisions 5 and 29).

## Decision 37: Reading the course again after each change

- **Chose:** After an instructor changes the lessons, the page asks the server for the course again instead of patching its own copy. Status moves and detail edits use the course the server sends back. The lesson list then starts afresh from what was saved, and the learners table and the feed reload too.
- **Rejected:** Updating the page's copy from each response.
- **Why:** Some changes have effects the page can't see. Removing a lesson renumbers the others, and adding or removing one changes every learner's "X of Y" (Decision 16). Asking again costs one small request per change and guarantees the page shows what was saved.

## Decision 38: Two instructors editing at once

- **Chose:** Course details and lessons are last write wins, and both edits stay in the activity log. A reorder based on an outdated list of lessons is refused with a 409, shown with a Reload button.
- **Rejected:** Version numbers on courses and lessons, to refuse any edit made from out-of-date data.
- **Why:** Any instructor can manage any course (Decision 3), but two of them editing the same course at the same moment is rare, and the log records both edits, so nothing is lost without trace. A reorder is different: it lists every lesson, so an outdated list would drop or repeat lessons, and the server refuses it (Decision 11). Version numbers would mean more code and a conflict screen on every form, the trade Decision 7 already turned down.

## Decision 39: How the activity feed reads

- **Chose:** Each entry says who, what in plain words, and when in the viewer's local time: "Priya Shah changed the title from "Old" to "New"", "added lesson 3, "Getting started"", "published the course". Long texts, such as a description or a lesson's content, are named rather than quoted, and a reorder just says "reordered the lessons". Comments show their text as plain text, with an "Instructor" label on instructors' comments. The feed loads 20 entries at a time with "Load older" (Decision 9) and reloads its newest page after every change made on the page.
- **Rejected:** Quoting old and new text in full, naming the new lesson order, and relative times such as "2 hours ago".
- **Why:** Plain sentences make the history readable. A 5,000-character description quoted twice would bury everything else. For a reorder the log keeps only lesson ids, and lessons removed since then couldn't be named. A relative time needs a timer to stay true, while a local date and time is exact and needs nothing. Learners only get comments (Decision 8), and a learner who isn't enrolled sees "Enrol to join the discussion" instead of the box (Decision 20).

## Decision 40: Bulk enrolment takes pasted text, and the server parses it

- **Chose:** One endpoint takes the list as text: `POST /courses/{id}/enrollments/bulk` with `{"text": ...}`. The server splits it on commas, semicolons, spaces and new lines, trims and lower-cases each address like `users.email`, drops repeats while keeping the first-seen order, and reports how many it dropped. An uploaded `.csv` or `.txt` file is read in the browser into the same box, so the instructor sees exactly what will be sent.
- **Rejected:** A separate file-upload endpoint, and parsing the list in the browser.
- **Why:** One parser on the server means pasting and uploading behave the same, and one set of tests covers both. Seeing the file's text before sending catches a wrong file. Known limitations: a quoted address in a CSV (`"a@b.com"`) comes back as invalid, because the server doesn't strip quotes, and a header row such as `email` shows as one invalid row.

## Decision 41: Five outcomes per address

- **Chose:** Each distinct address gets one outcome, in the order pasted: `enrolled`, `already_enrolled`, `unknown` (no account), `invalid` (not an email address), or `not_a_learner` (an instructor's account). The result also gives the count of each outcome and the number of repeats removed. The answer is 200, not 201.
- **Rejected:** Folding invalid addresses and instructor accounts into "unknown".
- **Why:** Goal 7 asks for three outcomes. The other two tell the instructor what to fix: a typo is different from a missing account, and an instructor can't be enrolled. It's a report with mixed outcomes, so 201 ("created") would claim too much.

## Decision 42: Bulk enrolment's rules and races

- **Chose:** Instructors only, with the role checked before the course is looked up. Published courses only: a draft or archived course gets a 409 for the whole request. One transaction, under the same shared lock on the course as self-enrolment. New rows go in with `INSERT ... ON CONFLICT DO NOTHING RETURNING`, and that alone decides "enrolled" versus "already enrolled"; there's no check beforehand. At most 500 distinct addresses and 200,000 characters; beyond that, or with no addresses at all, the answer is 422.
- **Rejected:** Checking for existing enrolments before inserting, one transaction per address, and enrolling into a draft.
- **Why:** The unique constraint stays the "already enrolled" check (Decision 18). A learner who enrols themselves at the same moment is reported as already enrolled, never as a 500, and with no check beforehand there's no gap for that race to fall into. The shared lock stops an archive from slipping in (Decision 7). The limits keep a single request bounded. The 422 comes from a new InvalidInput error, mapped in `main.py` like the others.

## Decision 43: The progress CSV

- **Chose:** `GET /courses/{id}/progress.csv` builds its rows from `course_progress()`, the same function as the Enrolled learners list: same learners, same order, instructors only. It uses Python's csv module and writes UTF-8 with a byte-order mark. Times are ISO 8601 in UTC to the second, and empty when they haven't happened yet. It's sent as an attachment named `course-<id>-progress-<UTC date>.csv`. Draft and archived courses can still be exported.
- **Rejected:** A second query for the file, local times, and UTF-8 without the mark.
- **Why:** One source of rows means the file can't disagree with the screen. UTC ISO times are unambiguous for spreadsheets and other tools. The byte-order mark makes Excel on Windows read names like "José Núñez" correctly, while other readers skip it when they decode with `utf-8-sig`. A course's history is kept when it's archived, so it can still be exported.

## Decision 44: Escaping spreadsheet formulas in the CSV

- **Chose:** A cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading apostrophe.
- **Rejected:** Writing cells exactly as typed, and stripping those characters.
- **Why:** Names are typed by people, and the file is made to be opened in Excel, where a name like `=HYPERLINK(...)` would run as a formula. The apostrophe makes the spreadsheet show the text as typed and run nothing. Stripping the characters would change the data.

## Decision 45: Downloading the CSV with the sign-in token

- **Chose:** The page fetches the file with the token in the header, turns it into a blob, and saves it under the filename from the server's Content-Disposition. CORS exposes that header to the frontend's origin.
- **Rejected:** A plain link, a token in the URL, and having the frontend make up its own filename.
- **Why:** The token travels in a header (Decision 1), which a plain link can't send. A token in the URL would end up in browser history and server logs. Exposing the header keeps the server as the one place that names the file.
