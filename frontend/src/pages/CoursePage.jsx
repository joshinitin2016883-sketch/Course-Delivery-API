import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { completeLesson, enroll, getCourse } from "../api/courses";
import { useAuth } from "../components/AuthProvider";
import LessonManager from "../components/LessonManager";
import ManageCourse from "../components/ManageCourse";
import { Empty, ErrorMessage, Loading } from "../components/States";
import { CourseStatusBadge, ProgressSummary } from "../components/Status";

export default function CoursePage() {
  const { courseId } = useParams();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollError, setEnrollError] = useState(null);

  useEffect(() => {
    let ignore = false; // set if another course opens before this answer arrives
    setCourse(null);
    setError(null);
    getCourse(courseId)
      .then((result) => {
        if (!ignore) {
          setCourse(result);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err.message);
        }
      });
    return () => {
      ignore = true;
    };
  }, [courseId]);

  async function handleEnroll() {
    setEnrolling(true);
    setEnrollError(null);
    try {
      await enroll(course.id);
      // Ask again: now that you're enrolled, the server sends the lessons' content and your progress.
      setCourse(await getCourse(course.id));
    } catch (err) {
      setEnrollError(err.message);
    } finally {
      setEnrolling(false);
    }
  }

  // A completion was saved: the server answered with your new progress.
  function updateProgress(progress) {
    setCourse((current) => ({ ...current, my_progress: progress }));
  }

  // After an instructor changes the lessons, ask the server for the course again, so the page shows the
  // lessons exactly as saved (removing one renumbers the others).
  async function reloadCourse() {
    setCourse(await getCourse(course.id));
  }

  if (error) {
    return (
      <div className="space-y-4">
        <ErrorMessage message={error} onRetry={() => window.location.reload()} />
        <BackLink />
      </div>
    );
  }
  if (course === null) {
    return <Loading />;
  }

  // Only a learner enrolled in this course gets my_progress.
  const progress = course.my_progress;
  const archived = course.status === "archived";
  // Which buttons show is presentation: the server refuses an enrolment or completion it doesn't allow.
  const canEnroll = user.role === "learner" && progress === null;
  const canComplete = progress !== null && !archived;

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <BackLink />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight wrap-break-word">{course.title}</h1>
          <CourseStatusBadge status={course.status} />
        </div>
        <p className="text-sm text-muted">
          <span className="capitalize">{course.category}</span> · {course.instructor.full_name}
        </p>
        <p className="max-w-prose whitespace-pre-wrap wrap-break-word">{course.description}</p>
      </div>

      {/* Instructors' tools. Showing them only to instructors is presentation: the API refuses anyone else. */}
      {user.role === "instructor" && <ManageCourse course={course} onChanged={setCourse} />}

      {canEnroll && (
        <div className="rounded-xl border border-line bg-surface p-6">
          <p>Enrol to see what's in each lesson and to track your progress.</p>
          <button type="button" onClick={handleEnroll} disabled={enrolling} className="btn-primary mt-4">
            {enrolling ? "Enrolling…" : "Enrol"}
          </button>
          {enrollError && (
            <div className="mt-4">
              <ErrorMessage message={enrollError} />
            </div>
          )}
        </div>
      )}

      {progress !== null && (
        <div className="space-y-3 rounded-xl border border-line bg-surface p-6">
          <h2 className="font-semibold">Your progress</h2>
          <ProgressSummary progress={progress} />
          {archived && (
            <p className="text-sm text-muted">
              This course has been archived. You can still read it, but you can't complete lessons in it any more.
            </p>
          )}
        </div>
      )}

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Lessons</h2>
        {/* Instructors edit the lessons, except on an archived course, which is read-only. Presentation
            only: the server refuses lesson changes from learners and on archived courses. The key changes
            whenever the saved lessons do, so the manager starts afresh from them. */}
        {user.role === "instructor" && !archived ? (
          <LessonManager
            key={course.lessons.map((lesson) => `${lesson.id}:${lesson.position}`).join(",")}
            course={course}
            onChanged={reloadCourse}
          />
        ) : course.lessons.length === 0 ? (
          <Empty title="This course has no lessons yet." />
        ) : (
          <ol className="space-y-4">
            {course.lessons.map((lesson) => (
              <LessonItem
                key={lesson.id}
                courseId={course.id}
                lesson={lesson}
                done={progress !== null && progress.completed_lesson_ids.includes(lesson.id)}
                canComplete={canComplete}
                onCompleted={updateProgress}
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/" className="text-sm font-medium text-accent hover:underline">
      <span aria-hidden="true">← </span>All courses
    </Link>
  );
}

// One lesson, in the order the server sends them. Its Mark complete button is busy only while its own
// request runs.
function LessonItem({ courseId, lesson, done, canComplete, onCompleted }) {
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState(null);

  async function handleComplete() {
    setCompleting(true);
    setError(null);
    try {
      onCompleted(await completeLesson(courseId, lesson.id));
    } catch (err) {
      // The server's reason, such as "This course is archived, so you can't complete lessons in it any more."
      setError(err.message);
    } finally {
      setCompleting(false);
    }
  }

  return (
    <li className="rounded-xl border border-line bg-surface p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="font-medium wrap-break-word">
          <span className="text-muted tabular-nums">{lesson.position}.</span> {lesson.title}
        </h3>
        {done && <span className="badge bg-success/10 text-success">Done</span>}
      </div>
      {/* The content is null until you enrol: the server leaves it out. It is plain text: React escapes it,
          so HTML in a lesson shows as typed and never runs. That is the defence Decision 1 relies on to keep
          the token in localStorage away from injected scripts. Line breaks are kept by whitespace-pre-wrap. */}
      {lesson.content !== null && (
        <div className="mt-3 max-w-prose whitespace-pre-wrap wrap-break-word">{lesson.content}</div>
      )}
      {canComplete && !done && (
        <button type="button" onClick={handleComplete} disabled={completing} className="btn-secondary mt-4">
          {completing ? "Saving…" : "Mark complete"}
        </button>
      )}
      {error && (
        <div className="mt-4">
          <ErrorMessage message={error} />
        </div>
      )}
    </li>
  );
}
