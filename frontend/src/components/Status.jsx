// How a course's status and a learner's progress are shown, the same way on every page.

const COURSE_STATUS_COLOURS = {
  draft: "bg-warning/10 text-warning",
  archived: "bg-line text-muted",
};

// "Draft" or "Archived". Published is the normal case, so it gets no label.
export function CourseStatusBadge({ status }) {
  if (status === "published") {
    return null;
  }
  return <span className={`badge capitalize ${COURSE_STATUS_COLOURS[status]}`}>{status}</span>;
}

const PROGRESS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
};

const PROGRESS_COLOURS = {
  not_started: "bg-line text-muted",
  in_progress: "bg-accent/10 text-accent",
  completed: "bg-success/10 text-success",
};

// A learner's state in a course: Not started, In progress or Completed.
export function ProgressBadge({ status }) {
  return <span className={`badge ${PROGRESS_COLOURS[status]}`}>{PROGRESS_LABELS[status]}</span>;
}

// A learner's progress through one course: its state, and how many of its lessons they have done.
// Takes the server's progress (or enrolment) object, which has status, lessons_done and lessons_total.
export function ProgressSummary({ progress }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <ProgressBadge status={progress.status} />
      <span className="text-sm text-muted tabular-nums">
        {progress.lessons_done} of {progress.lessons_total} lessons done
      </span>
    </span>
  );
}
