
# Plan

## How did you break the work into sessions?

- Session 1: backend scaffold, sign-in and roles (step 1).
- Session 2: courses, lessons and the activity log (step 2).
- Session 3: course states, comments and the activity feed (step 3), one commit per change.
- Git was set up after step 2, so steps 1 and 2 share one commit; from step 3 on, every change has its own commit.

## What order did you build in, and why that order?

- Backend first: every rule in the brief must be enforced on the server, so I built and tested the rules before any screen.
- Sign-in first, because every other endpoint depends on who the user is and what role they have.
- Courses and lessons before states, because publishing needs lessons to exist.
- States and the activity log before enrolment, because learners enrol in published courses, and every change has to be logged from the start.

## What did you estimate versus what it actually took?

| Step                              | Estimate      | Actual |
| --------------------------------- | ------------- | ------ |
| 1. Sign-in and roles              | not estimated | 1 h    |
| 2. Courses, lessons, activity log | not estimated | 0.5 h  |
| 3. Course states and the feed     | 1.5 h         | 1 h    |

## What did you cut when you ran short?

Nothing yet.
