import { useState } from "react";
import { changeStatus, updateCourse } from "../api/courses";
import ConfirmButton from "./ConfirmButton";
import CourseForm from "./CourseForm";
import { ErrorMessage } from "./States";

// The one move the server allows from each status (course_service.MOVES in the backend). Showing only that
// button is presentation: the server checks every move, and when it refuses, for example publishing a
// course with no lessons, its message is shown here.
const NEXT_MOVE = {
  draft: { move: "publish", label: "Publish", busyLabel: "Publishing…" },
  published: { move: "archive", label: "Archive", busyLabel: "Archiving…" },
  archived: { move: "restore", label: "Restore", busyLabel: "Restoring…" },
};

// The instructor's tools for the course itself: its status and its details. Any instructor may manage
// any course (Decision 3). onChanged receives the course as the server now has it.
export default function ManageCourse({ course, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState(null);
  const next = NEXT_MOVE[course.status];
  const archived = course.status === "archived";

  async function runMove() {
    setMoving(true);
    setError(null);
    try {
      onChanged(await changeStatus(course.id, next.move));
    } catch (err) {
      setError(err.message);
    } finally {
      setMoving(false);
    }
  }

  // CourseForm shows the server's message if this throws.
  async function saveDetails(values) {
    const updated = await updateCourse(course.id, values);
    setEditing(false);
    onChanged(updated);
  }

  return (
    <section className="space-y-4 rounded-xl border border-line bg-surface p-6">
      <h2 className="font-semibold">Manage this course</h2>
      {archived && (
        <p className="text-sm text-muted">This course is archived and read-only. Restore it to make changes.</p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        {next.move === "archive" ? (
          <ConfirmButton
            label="Archive"
            question="Archive this course? It leaves the catalogue and progress in it is frozen. You can restore it later."
            confirmLabel="Archive"
            busyLabel={next.busyLabel}
            onConfirm={runMove}
          />
        ) : (
          <button type="button" onClick={runMove} disabled={moving} className="btn-primary">
            {moving ? next.busyLabel : next.label}
          </button>
        )}
        {!archived && !editing && (
          <button type="button" onClick={() => setEditing(true)} className="btn-secondary">
            Edit details
          </button>
        )}
      </div>
      {error && <ErrorMessage message={error} />}
      {editing && (
        <CourseForm
          initial={course}
          submitLabel="Save changes"
          busyLabel="Saving…"
          onSubmit={saveDetails}
          onCancel={() => setEditing(false)}
        />
      )}
    </section>
  );
}
