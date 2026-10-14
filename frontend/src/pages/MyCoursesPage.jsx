import { useEffect, useState } from "react";
import { Link } from "react-router";
import { listMyCourses } from "../api/courses";
import { Empty, ErrorMessage, Loading } from "../components/States";
import { CourseStatusBadge, ProgressSummary } from "../components/Status";

// Every course you are enrolled in, newest enrolment first, with your progress in each.
// Only learners have enrolments: for anyone else the server answers 403, shown as the error.
export default function MyCoursesPage() {
  const [enrollments, setEnrollments] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listMyCourses()
      .then(setEnrollments)
      .catch((err) => setError(err.message));
  }, []);

  let content;
  if (error) {
    content = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (enrollments === null) {
    content = <Loading />;
  } else if (enrollments.length === 0) {
    content = (
      <Empty title="You aren't enrolled in any courses yet.">
        <Link to="/" className="font-medium text-accent hover:underline">
          Find a course to enrol in
        </Link>
      </Empty>
    );
  } else {
    content = (
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {enrollments.map((enrollment) => (
          <li
            key={enrollment.course.id}
            className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0 wrap-break-word">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/courses/${enrollment.course.id}`} className="font-medium hover:text-accent hover:underline">
                  {enrollment.course.title}
                </Link>
                {/* An archived course stays in this list: you can still read it, but not complete it. */}
                <CourseStatusBadge status={enrollment.course.status} />
              </div>
              <p className="mt-1 text-sm text-muted capitalize">{enrollment.course.category}</p>
            </div>
            <ProgressSummary progress={enrollment} />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">My courses</h1>
      {content}
    </div>
  );
}
