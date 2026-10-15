# Architecture

## The moving pieces, and how they talk

Three pieces, each on a free tier:

```
 Browser: the React app ─────── its files come from Vercel
      │
      │  HTTPS and JSON, with "Authorization: Bearer <token>"
      │  CORS allows only the exact origins in CORS_ORIGINS
      ▼
 Render: the FastAPI API ── router → service → SQLAlchemy models
      │
      │  psycopg 3 over TLS, with Neon's direct connection string
      ▼
 Neon: Postgres 17
```

- **The React app** (React 19, React Router 7, Tailwind 4, plain JavaScript) runs in the browser. Every call to the API goes through one function, `send()` in `frontend/src/api/client.js`. It adds the token, turns an error answer into an `ApiError` carrying the server's message, signs the user out on a 401, and reports any request that takes longer than 3 seconds.
- **Signing in:** `POST /auth/login` returns a JWT (HS256) that holds only the user's id and an expiry 8 hours later. The app keeps it in localStorage and sends it as a Bearer header on every request. There are no cookies (Decision 1). For each request the API looks the user up, role included, in the database (`get_current_user` in `app/core/deps.py`). The page learns who is signed in from `GET /auth/me` (Decision 27).
- **CORS:** the app and the API have different origins, so `CORSMiddleware` in `app/main.py` lets in only the exact origins listed in `CORS_ORIGINS` (Decision 23). It also exposes `Content-Disposition`, for the CSV's filename (Decision 45).
- **The API** (FastAPI, SQLAlchemy 2.0, Alembic, Pydantic) has three layers:
  - Routers in `app/routers/` check the request against a Pydantic schema (a bad body gets a 422) and call one service function.
  - Services in `app/services/` hold every rule: roles, state moves, row locks, and the activity log row written in the same transaction as each course change.
  - When a rule is broken, a service raises an error from `app/services/errors.py`. One handler in `app/main.py` maps it to 401, 403, 404, 409 or 422, with `{"detail": "<message>"}`, and the page shows that message.
- **Postgres** stores everything, and is also the last line of defence. Its CHECKs, unique constraints, a RESTRICT foreign key and the activity log's append-only trigger hold even if a service is wrong (`docs/schema.md`). Alembic migrations 0001–0006 build it.

## Where each piece runs

- **The React app:** static files on Vercel's free Hobby plan, built from `frontend/` with `npm run build`.
  - The API's address (`VITE_API_URL`) is written into the build, so changing it needs a redeploy.
  - `vercel.json` sends every path to `index.html`, so reloading a page such as `/courses/12` works.
- **The API:** a free Render web service running Python 3.12, in Singapore.
  - It sleeps after 15 minutes without traffic, and the next request takes about a minute to answer. Once any request has run for 3 seconds, the app shows "Waking the server, this can take up to a minute…" (`WakingBanner.jsx`).
  - The free tier has no shell and no pre-deploy step, so the start command runs `python -m alembic upgrade head` before uvicorn. When the database is already at the latest version, the migration does nothing (Decision 23).
  - `/health` doesn't touch the database, so Render's health checks don't wake Neon.
- **The database:** Postgres 17.11 on Neon's free plan, also in Singapore, reached through the direct connection string.
  - It suspends after 5 idle minutes and wakes in a few hundred milliseconds.
  - `pool_pre_ping` replaces any pooled connection Neon has closed, so the first request after a pause doesn't fail.

The secrets, `DATABASE_URL` and `JWT_SECRET`, live only in Render's environment, and `app/core/config.py` refuses to start without them. The demo seed runs against Neon from a developer's machine, never from Render (`docs/deploy.md`). Locally, Docker runs two Postgres databases: one for development, and one that the tests wipe and rebuild.

## One action, end to end: a learner marks a lesson complete

1. **The click.** `LessonItem.handleComplete` in `frontend/src/pages/CoursePage.jsx` disables the button, which now reads "Saving…", and calls `completeLesson(courseId, lessonId)` in `frontend/src/api/courses.js`.
2. **The client.** `apiRequest` calls `send()`, which sends `POST /courses/{course_id}/lessons/{lesson_id}/complete` to `VITE_API_URL` with the Bearer token. The Authorization header makes this a cross-origin request that needs permission first, so the browser sends a preflight `OPTIONS` request, which `CORSMiddleware` answers for allowed origins.
3. **The router.** `complete_lesson` in `app/routers/enrollments.py` gets a database session from `get_db` and the user from `get_current_user`. A bad or expired token is a 401 here, and the app goes to the sign-in page. Otherwise it calls `enrollment_service.complete_lesson(db, user, course_id, lesson_id)`.
4. **The service.** `complete_lesson` in `app/services/enrollment_service.py` does all of this in one transaction:
   - `require_learner` refuses instructors with a 403.
   - `course_service.lock_course_for_share` loads the course `FOR SHARE`. Completions don't block each other, but an archive or a lesson removal, which lock the course `FOR UPDATE`, waits for them, and they wait for it (Decision 7). `can_see` turns a draft, or an archived course the learner isn't enrolled in, into a 404.
   - The learner's enrolment is loaded `FOR UPDATE`. Like every other change, it locks the course first and the enrolment second, so two requests can't deadlock. With no enrolment the answer is 403 ("Enrol in this course first."), and a lesson from another course is a 404.
   - **On an archived course** the answer is 409: "This course is archived, so you can't complete lessons in it any more." (Decision 17). The page hides Mark complete on archived courses, so a learner only meets this when the course was archived after their page loaded.
   - **If the lesson isn't done yet,** it adds one `LessonCompletion` row. The row and the enrolment's times share one timestamp, taken once from `datetime.now(timezone.utc)`. The first completion moves the enrolment from not started to in progress and sets `started_at`. Every new completion sets `last_activity_at`, which the inactivity alerts read (Decision 50). Doing the last remaining lesson moves the enrolment to completed and sets `completed_at`. Each move goes through `_move`, which allows only the two steps in the `PROGRESS_MOVES` table (Decision 14). Then `db.commit()`. Completions aren't written to the activity log (Decision 22).
   - **If the lesson is already done,** nothing is written. Because of the enrolment's row lock, two requests at once run one after the other, and the second sees the first's completion. The unique (enrollment_id, lesson_id) and the status CHECKs back this up in the database.
5. **The response.** `_progress` builds a `ProgressOut`: the status, lessons done and in total, the ids of the completed lessons, and the times. FastAPI sends it as JSON with a 200. A repeated completion gets the same 200 and the same progress. When a rule is broken, the service's error becomes its status code and message in `main.py` instead.
6. **The page.** `updateProgress` puts the new progress into the page's course state, and React redraws the page. The lesson gets its "Done" badge and loses its button, and "Your progress" shows the new state and the new "X of Y lessons done", with no second request. On an error, the server's message appears under that lesson. On the page itself, a second click can't happen: the button is disabled while its request runs and gone once the lesson is done. A repeat comes only from another tab or a direct API call.

## What I decided not to build, and why

- **Unenrolling** (Decision 21): the brief doesn't ask for it, and it would need rules for the learner's completions and history, which must be kept.
- **Undoing a completed lesson** (Decision 31): goal 4 allows only Not started → In progress → Completed. Undoing would also rewrite the completions the dashboard counts and the alerts depend on.
- **Course ownership** (Decision 3): any instructor can manage any course. `instructor_id` records who created it, and the activity log records who changed what.
- **Refresh tokens and cookies** (Decision 1): the app and the API are on different sites, so cookies would need cross-site settings and CSRF protection. After 8 hours you sign in again.
- **Announcements to enrolled learners:** an instructor's comment on a course already reaches everyone enrolled in it (Decision 20).
- **A background job for alerts** (Decision 50): alerts are worked out when they're read, so there's nothing to schedule. A free Render service that sleeps couldn't run a job reliably anyway.
- **Per-instructor dismissals** (Decision 51): instructors share every course (Decision 3), so a dismissal hides the alert for all of them.
- **The stretch ideas:** quizzes, certificates, discussion threads per lesson, prerequisite courses, video lessons, ratings and reviews, learning paths, downloadable resources, and an email digest of inactive learners. The brief says none of them substitutes for a goal, and the time went into the ten goals and their tests. The email digest would also need email delivery and a scheduled job, the same problem as an alerts job.

Smaller choices of the same kind are in the decisions: no self sign-up (Decision 2), plain-text lessons (Decision 28), and up/down buttons instead of drag and drop (Decision 34).
