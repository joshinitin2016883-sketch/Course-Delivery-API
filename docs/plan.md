# Plan

## How did you break the work into sessions?

- Session 1: backend scaffold, sign-in and roles (step 1).
- Session 2: courses, lessons and the activity log (step 2).
- Session 3: course states, comments and the activity feed (step 3), one commit per change.
- Git was set up after step 2, so steps 1 and 2 share one commit; from step 3 on, every change has its own commit.
- Session 4: enrolment and progress (step 4), in three commits plus the decisions.
- Session 5: deploying the API to Render and Neon (step 6a), then course search (step 5).
- Session 6: the learner frontend on Vercel (step 6b), in four commits plus the decisions, and schema.md.
- Session 7: the instructor screens (step 7) in five commits, then bulk enrolment and the CSV export (step 8) in five, each step followed by its decisions.
- Session 8: the dashboard, inactivity alerts and demo data (step 9) in five commits, then the final docs, the final seed on Neon and the submission (step 10).

## What order did you build in, and why that order?

- Backend first: every rule in the brief must be enforced on the server, so I built and tested the rules before any screen.
- Sign-in first, because every other endpoint depends on who the user is and what role they have.
- Courses and lessons before states, because publishing needs lessons to exist.
- States and the activity log before enrolment, because learners enrol in published courses, and every change has to be logged from the start.
- Enrolment and progress next, because they are the core of the brief: the spreadsheet couldn't tell who had finished a course.
- I deployed the API before building search, earlier than my build map said. My last project's first deploy hit several environment problems, and I wanted those surprises while the app was still small. This one hit three: no root directory, Python 3.14 by default, and unsaved environment variables.
- Search before the first screen, because the course list is the first page a learner sees.
- The learner screens before the instructor screens, so the core flow (sign in, find a course, enrol, complete lessons) worked at a live URL as early as possible.
- The instructor screens before goals 7, 8 and 10, because bulk enrolment, the learners table and the CSV all live on the instructor's course page.
- Bulk enrolment and the CSV before the dashboard and alerts. The CSV reuses the progress list the learners table already had, so it was the cheapest goal left.
- The dashboard and alerts last, because they only read what every other feature writes. The demo seed came after them, since it has to produce data for every screen.

## What did you estimate versus what it actually took?

| Step                              | Estimate      | Actual  |
| --------------------------------- | ------------- | ------- |
| 1. Sign-in and roles              | not estimated | 1 h     |
| 2. Courses, lessons, activity log | not estimated | 0.5 h   |
| 3. Course states and the feed     | 1.5 h         | 1 h     |
| 4. Enrolment and progress         | 2 h           | 2 h     |
| 5. Course search                  | 1 h           | 1.5 h   |
| 6. Deploy and learner frontend    | 2.5 h         | 5.5 h   |
| 7. Instructor screens             | not estimated | 1.25 h  |
| 8. Bulk enrolment and CSV         | not estimated | 0.5 h   |
| 9. Dashboard, alerts, demo data   | not estimated | 1.5 h   |
| 10. Docs, final seed, submission  | not estimated | 2 h     |

The actual times are read from my commit times. In all it took about 17 hours against a 12-hour budget.

Step 6 took more than twice its estimate:

- The first deploy failed three times before it worked, and I had to rotate the database password after pasting the connection string into a chat by mistake.
- My frontend spec left out two filters that goal 6 asks for (status and instructor). Adding them needed a new endpoint, GET /instructors.
- One commit swallowed the course-list files by accident, and I split it back into two before carrying on.
- The agent checked every page in a real browser and proved each check could fail, which is slow but caught real problems.

By the end of step 6 I had used about 11 of the 12 hours, with the instructor screens and goals 7, 8 and 10 still to build. I didn't re-estimate steps 7 to 10 one by one. I chose to finish all ten goals rather than stop at the budget, and kept each later step smaller instead: lighter browser checks, and mutation checks only for the key rules.

Steps 7 to 9 went faster than step 6 because the backend for them mostly existed and the patterns were set: services raise errors, the page shows the server's message, and each commit stops for review. What still took time was checking, and the checks paid for themselves:

- A phone-width check found the enrolled-learners table widening the whole page (step 7).
- A daylight-saving test found two time-zone bugs in the dashboard's weekly chart (step 9, Decision 48).
- Checking architecture.md against the code found that completing a lesson used two clocks (step 10, Decision 47).

## What did you cut when you ran short?

None of the ten goals. What I cut to fit them in:

- **Automated frontend tests in the repo.** The agent checked every screen in a real browser, and broke each key rule on purpose to prove its check failed. Those scripts ran from its scratch folder and aren't in the repository. Only the backend suite (pytest) is.
- **Continuous integration.** The tests run on my machine before each commit, not on GitHub.
- **A visual polish pass.** The screens are plain on purpose. I chose to spend the time on the ten goals and the documents rather than on looks.

Not built by choice, rather than for time:

- Undoing a completed lesson. Goal 4 rejects any backward move (Decision 31).
- Announcements to enrolled learners. Comments on the course already reach them (Decision 20).
- The stretch ideas. The brief says none of them makes up for a goal (architecture.md lists them).
