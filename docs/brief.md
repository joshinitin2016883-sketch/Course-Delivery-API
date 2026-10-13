# Assignment 05 — Course Delivery & Enrollment

## The scenario

Picture a company running internal training — onboarding material, compliance courses, skills
workshops — built by a couple of instructors and worked through by everyone else at their own pace.
Right now a course is a folder of slide decks and PDFs emailed around, and whether anyone actually
finished it is tracked, if at all, in a spreadsheet someone updates when they remember.

The result is predictable. A course goes out to the whole company before anyone notices it is just a
title page with nothing behind it. A learner starts a course, gets busy, and quietly stops halfway
through, and nobody notices until someone asks why their certificate never arrived. Nobody can say
with any confidence how many people have actually finished the mandatory compliance course versus
merely opened it once.

They want one system where instructors build and publish courses, learners work through them at
their own pace, and progress is tracked automatically rather than self-reported. Instructors should
be able to see, at a glance, who has finished, who is partway through, and who has gone quiet. Build
the tool that replaces the spreadsheet.

## What it must do

Everything below is required. Several of the ten spell out exact rules — what happens on an illegal
move, what a bulk action must report back, when a dismissed alert is allowed to reappear — and those
specifics are the actual ask, not just the bold headline in front of them.

1. **Accounts and roles.** People sign in with an email and password, and there are at least two
roles — an instructor role and a learner role. Instructors can create, edit, publish and archive
courses, manage lessons, and enrol learners. Learners can enrol themselves in a published course,
see the courses they are enrolled in, and track their own progress — they cannot edit course
content, enrol other learners, or see other learners' progress. The difference must be enforced on
the server, not just hidden in the interface.

2. **Courses.** Instructors create courses with a title, a description and a category, and can edit
them later. Courses can be archived and restored. Archiving removes a course from the catalogue
without deleting its lessons or any learner's enrollment history.

3. **Lessons inside courses.** Every lesson belongs to exactly one course and carries a title, its
content or a description, and a position in the course's running order. Lessons can be added,
edited, reordered and removed by the instructor. Opening a course shows its lessons in order.

4. **Course and progress states.** A course moves *Draft → Published → Archived*. Publishing is
blocked unless the course already has at least one lesson — the server rejects an attempt to publish
an empty course, with a message explaining why. Once a learner is enrolled, their own progress
through that course moves *Not Started → In Progress → Completed* as they work through its lessons,
tracked separately for every learner on every course. Any other move in either sequence is rejected
by the server.

5. **Enrollment.** Instructors enrol learners into a published course, or learners can enrol
themselves, and either way a learner can be enrolled in any number of courses while a course can
have any number of learners. Every learner can see one list of every course they are enrolled in,
alongside their progress in each.

6. **Finding courses.** One list shows every course the viewer can see — published courses for
learners, every course including drafts and archives for instructors — with a text search over
titles and descriptions, filters for category, status and instructor, sorting by title, creation
date or enrollment count, and pagination showing the total number of matches. All of this must
happen on the server — do not load every course into the browser and filter there.

7. **Bulk enrollment.** An instructor can bulk-enrol learners into a course by pasting or uploading
a list of email addresses. The result must report, per address, whether it matched an unknown
address, an already-enrolled learner, or was newly enrolled. Separately, export the progress of
every learner enrolled in a course as a CSV file.

8. **A dashboard.** A landing view shows headline numbers — total learners, published courses,
completions this month, learners currently in progress. It also breaks enrollments down by course
and by progress state, and charts completions over the last eight weeks.

9. **History you cannot rewrite.** Every course has an activity log recording when it was created,
every edit, every publish or archive transition and who made it, and any comments learners or the
instructor leave. Nothing in this log can be edited or deleted after the fact, including by the
instructor.

10. **Inactivity alerts.** Any learner whose progress on a course is In Progress but who has made no
further progress for more than fourteen days appears in an alerts area for the instructor, with a
count badge visible in the navigation. An instructor can dismiss an alert for a specific learner and
course. If that learner then engages again and later goes quiet for the same length of time, the
alert reappears.

## Stretch ideas (optional)

None of these are required, and none substitute for a goal above. If you finish all ten with time
left over, pick whichever of these sounds most useful and build it:

- Quizzes with automatic scoring.
- Certificates on completion.
- Discussion threads per lesson.
- Prerequisite courses that gate enrollment.
- Video lessons with watch-progress tracking.
- Course ratings and reviews.
- Learning paths bundling several courses.
- Downloadable resources per lesson.
- An email digest of inactive learners.


---

## What we are assessing

A working application is table stakes. Almost every serious candidate will produce something that runs, has a login, and roughly does what was asked. That's the floor, not the differentiator.

What actually separates submissions is the record of thinking behind the app: the decisions you made and why, the trade-offs you weighed, what you built first and what you deliberately left out, and whether you can explain any part of your own system when asked. We are hiring for judgement. The app is the evidence for that judgement, not the deliverable in itself.

We also read the code itself for structure and readability, which counts for a small share of the overall score.

## Time budget

Budget about 12 hours total, spent roughly 2 hours a day across a week.

This is not a race. We are not timing you against other candidates, and submitting early scores nothing extra. Twelve hours is a size guide so you know how much to attempt — pace yourself, stop when you're tired, and spend some of that time thinking and documenting, not only typing code.

## Pick any stack you like

Use any language, any framework, any UI library, any ORM, and any database access approach you want. We have no house stack, and no stack scores better than another — this round is not a test of whether you know particular tools.

Use whatever you are fastest and most confident in. Time spent learning something new to impress us is time not spent on the ten goals above, and it will show.

## Using AI is allowed and encouraged

Use AI tools however you want — to scaffold code, debug a stuck problem, write tests, draft documentation, or anything else that helps you move faster. A few things to know about how we treat it:

- We do not penalise AI use, and we make no attempt to detect it.
- We care about whether you understood, directed and verified the output — not about who or what produced the first draft of it.
- `docs/ai-prompts.md` must contain the prompts you actually used, including the ones that produced bad output and what you changed afterwards. If you used no AI at all, say so here and describe how you worked instead — that is assessed the same way.
- Submitting generated code you cannot explain is the single most common way candidates fail this round.

You are accountable for everything in your submission. If a reviewer points at a piece of code and asks why it's there, or why it works the way it does, "the AI wrote it" is not an answer.

## Use git properly

Publish to a public GitHub repository, and commit incrementally as the work actually happens — after each meaningful step, not in one pass at the end.

A repository whose entire history is a single "initial commit" containing a finished app scores zero on git history, and it colours how we read everything else in your submission, however good the app itself is. Your history is how we see the order you built in, where you got stuck, and how the design changed along the way. If it isn't there, we can't assess it, and we won't assume the best.

## What you must commit

Alongside your code, commit these five files under `docs/`. Your zip includes a stub for each with the questions it needs to answer — fill them in as you go, not from memory at the end.

| File | What it must answer |
|------|----------------------|
| `docs/architecture.md` | What the moving pieces are, how they talk to each other, where each one runs, the request path for one representative user action end to end, and what you decided not to build. |
| `docs/schema.md` | Every table's columns and types, which relationships are one-to-many versus many-to-many, which constraints live in the database versus the application, what you deliberately denormalised, and what would break first at 100x the data. |
| `docs/plan.md` | How you split the work into sessions, what order you built in and why, what you estimated versus what it actually took, and what you cut when you ran short. |
| `docs/decisions.md` | At least five real decisions — what you chose, what you rejected, and why — including at least one you later reversed. |
| `docs/ai-prompts.md` | The prompts you actually used, in order, grouped by what you were trying to do, including at least one that produced something wrong and what you did about it. |

## Host it for free

Deploy the whole thing somewhere reachable by URL, using free tiers only.

One combination that works, if you would rather not decide:

- **Database** — a managed service such as Supabase.
- **Server-side code** — Render.
- **Browser-side code** — Vercel.

Deploy in that order: create the database first, give the server its connection details as environment variables, then point the browser-side part at the server's public URL.

This is one option, not a requirement. Any free host is equally acceptable — everything on a single provider, one virtual machine, a container platform, a static host with serverless functions. The choice earns and loses nothing.

Requirements:

- A working live URL.
- Seeded with enough demo data to show the system doing something, not an empty shell.
- Demo credentials for every role recorded in `SUBMISSION.md`.
- Connection strings, keys and passwords kept in environment variables, never in the repository.
- Free tiers often sleep when idle and can take a minute or more to wake. Note it in `SUBMISSION.md` if yours does, so a slow first load is not read as a broken deployment.
- If you cannot get it hosted, submit anyway and record in `SUBMISSION.md` what you tried and where it broke.

## How to submit

Send us:

- The URL of your public GitHub repository.
- The URL of your live, deployed application.
- Your completed `SUBMISSION.md`, committed to the repository.

That's the whole submission. Nothing else to prepare, no separate form.

## What happens next

If your submission clears the bar, we'll set up a short call. We will ask about specific decisions we can see in your repository and its history — why you modelled something a particular way, what a certain commit was fixing, what you'd change if you kept going.

We're telling you this now because it should change how carefully you document as you go. Write `docs/decisions.md` for a version of yourself who has to explain it three weeks from now.

## Scope

The 10 goals stated in this brief are the cutoff. Meet all 10, solidly, and you have a complete submission.

Stretch ideas are optional. They exist for candidates who finish the 10 with time left and want to keep building — they are never required, and they do not make up for a goal you didn't hit. Doing 8 goals well beats doing 10 goals badly. If time is short, finish fewer goals properly rather than leaving all ten half-done.
