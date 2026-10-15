# Submission

## Links

- **GitHub repository:** https://github.com/joshinitin2016883-sketch/course-delivery-api
- **Live application:** https://course-delivery-app.vercel.app
- **Live API:** https://course-delivery-api.onrender.com (interactive docs at `/docs`)

## Notes for the reviewer

- **The first load can take up to a minute.** The API runs on Render's free tier, which sleeps after 15 idle minutes. If a request takes more than 3 seconds, the app says "Waking the server, this can take up to a minute…". Once it's awake, pages answer quickly. The database (Neon's free tier) also suspends when idle, but wakes in under a second.
- **The demo data was seeded on 15 October 2026,** with every time relative to that moment. As days pass, the numbers drift: completions slide out of the 8-week chart, "completions this month" resets on the 1st, and more learners go quiet. Before a demo I reset the database and seed again (`docs/deploy.md`).
- **Where to look first:**
  - Sign in as the instructor. You land on the dashboard. Alerts in the nav shows 4 learners who have gone quiet.
  - Open a course to see the instructor tools: status moves, lessons, enrolled learners, bulk enrolment, the CSV download and the activity feed.
  - Sign in as the learner (Alex Chen). Alex is one of the quiet learners, on "Python for analysts". Complete a lesson there, then sign in as the instructor again: Alex's alert has gone.
- **Every rule is enforced on the server.** Buttons are hidden by role only as presentation. The API refuses anything the role or state doesn't allow, and the page shows the server's message.
- **Where the reasoning is:** `docs/decisions.md` (53 decisions, one reversed), `docs/architecture.md`, `docs/schema.md`, `docs/plan.md` and `docs/ai-prompts.md`. Deployment steps are in `docs/deploy.md`.

## Demo credentials

Every demo account has the same password: `Abcd@1234`.

| Role | Email | Password |
|------|-------|----------|
| Instructor | instructor@example.com (Priya Shah) | Abcd@1234 |
| Instructor | instructor2@example.com (Daniel Okafor) | Abcd@1234 |
| Learner | learner@example.com (Alex Chen) | Abcd@1234 |
| Learner | maria@example.com, sam@example.com, jordan@example.com, fatima@example.com | Abcd@1234 |

The demo seed adds 20 more learners (aisha@example.com, ben@example.com and others), all with the same password. There's no sign-up: accounts come only from the seed (Decision 2).

## Stack

| Layer | What you used | Why |
|-------|---------------|-----|
| Frontend | React 19, React Router 7, Tailwind 4, Vite; plain `fetch`, no component or state library | Small and familiar. Every API call goes through one function, so the token, errors and the slow-server banner are handled in one place. |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt | Typed request checks and short routers. Every rule lives in a service, and each broken rule raises an error that one handler maps to a status code. |
| Database | PostgreSQL 17 (Neon in production, Docker locally) | Row locks for the state rules, constraints and a trigger as the last line of defence, and real aggregates for search and the dashboard. |
| Hosting | Render (API), Vercel (frontend), Neon (database), all free tiers, Render and Neon in Singapore | The combination the brief suggests. The API and the database are in the same region, so queries don't cross continents. |

## Goal checklist

| # | Goal | Status | Notes |
|---|------|--------|-------|
| 1 | Accounts and roles | Done | Email and password sign-in, two roles, checked on the server for every endpoint. The role is read from the database on each request, never from the token (Decisions 1, 2, 29). |
| 2 | Courses | Done | Create and edit; archive and restore. Archiving keeps lessons and every learner's history (Decisions 5, 17). |
| 3 | Lessons inside courses | Done | Add, edit, reorder (one request, one log entry) and remove; shown in order (Decisions 11, 12, 15, 34). |
| 4 | Course and progress states | Done | Each moves only through its allowed steps; any other move gets a 409. An empty course can't be published, and the server says why. Progress comes from completed lessons, never set by hand (Decisions 5, 14, 16, 31). |
| 5 | Enrolment | Done | Learners enrol themselves; instructors enrol in bulk; "My courses" lists every enrolment with its progress (Decisions 18, 19). |
| 6 | Finding courses | Done | Search, filters for category, status and instructor, three sorts, and pages with the total, all on the server (Decisions 24, 25, 26, 30). |
| 7 | Bulk enrolment and CSV | Done | Paste or upload; one outcome per address, including the brief's three. The CSV of every enrolled learner's progress is safe to open in Excel (Decisions 40 to 45). |
| 8 | Dashboard | Done | Four headline numbers, enrolments by course and state, and completions over the last 8 weeks (Decisions 46 to 49). |
| 9 | History you cannot rewrite | Done | Every change and comment is logged in the same transaction. A database trigger refuses any update or delete of a log row (Decisions 6, 8, 22, 39). |
| 10 | Inactivity alerts | Done | More than 14 days quiet while in progress. A count badge in the nav. A dismissal covers one quiet spell, so the alert comes back after the learner is active and goes quiet again (Decisions 50 to 52). |

Tests: 242 backend tests (pytest) against a separate test database. Each key rule was also broken on purpose to prove its test fails.

## How much time did you actually spend?

About 17 hours against the 12-hour budget, read from my commit times (`docs/plan.md` has the step-by-step table). Step 6, the deploy and the first frontend, took 5.5 hours against an estimate of 2.5. By then I had used about 11 hours, so steps 7 to 10 ran over the budget. I chose to finish all ten goals rather than stop with three missing.

## What would you do next, with another 12 hours?

1. **Move the browser checks into the repo** as Playwright tests, and run them and pytest in GitHub Actions on every push. Today the browser checks live outside the repository.
2. **Make the alerts badge cheaper.** It fetches the whole alert list on every page change. I'd add a count-only answer and an index that the alert rule can use (`docs/schema.md`, "At 100x").
3. **A "Revisit later" checklist for learners:** a private tick-box per lesson, separate from Mark complete, so a learner can mark lessons to re-read without touching their progress (Decision 31).
4. **The email digest of inactive learners** from the stretch list, sent weekly. It needs a scheduler that a sleeping free server can't provide, so a paid tier or an external cron.

## What are you least happy with in this codebase, and why?

The frontend's tests aren't in the repository. The agent checked every screen in a real browser and broke each key rule on purpose to prove its check failed, but those scripts ran from its scratch folder. A reviewer can run the 242 backend tests, but has to take the frontend checks on trust.

The demo data also goes stale. It's realistic on the day it's seeded, but the dashboard and alerts drift as days pass, so I have to re-seed before each demo.
