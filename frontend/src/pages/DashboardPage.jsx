import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getDashboard } from "../api/dashboard";
import { Empty, ErrorMessage, Loading } from "../components/States";
import { CourseStatusBadge } from "../components/Status";
import WeeklyCompletionsChart from "../components/WeeklyCompletionsChart";

// The instructors' landing page (goal 8). Only instructors get the link; for anyone else the server
// answers 403, shown as the error.
export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboard()
      .then(setDashboard)
      .catch((err) => setError(err.message));
  }, []);

  let content;
  if (error) {
    content = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (dashboard === null) {
    content = <Loading />;
  } else {
    content = (
      <div className="space-y-10">
        {/* Each tile says exactly what it counts, since "learners" could mean several things. */}
        <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Tile label="Learners" value={dashboard.learners} note="Every learner account." />
          <Tile label="Published courses" value={dashboard.published_courses} note="Open for enrolment now." />
          <Tile
            label="Completions this month"
            value={dashboard.completions_this_month}
            note="Courses completed since the 1st (UTC)."
          />
          <Tile
            label="Learners in progress"
            value={dashboard.learners_in_progress}
            note="Each counted once. Archived courses aren't counted."
          />
        </dl>

        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Course completions per week</h2>
          <div className="rounded-xl border border-line bg-surface p-4">
            <WeeklyCompletionsChart weeks={dashboard.completions_by_week} />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Enrolments by course</h2>
          <CourseBreakdown rows={dashboard.by_course} />
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      {content}
    </div>
  );
}

function Tile({ label, value, note }) {
  return (
    <div className="flex flex-col rounded-xl border border-line bg-surface p-4">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="order-first text-3xl font-semibold">{value}</dd>
      <dd className="mt-1 text-xs text-muted">{note}</dd>
    </div>
  );
}

const STATE_COLUMNS = ["Not started", "In progress", "Completed"];

// Every course with at least one enrolment, sorted by title, with how many learners are in each state.
function CourseBreakdown({ rows }) {
  if (rows.length === 0) {
    return <Empty title="No learners are enrolled in any course yet." />;
  }
  return (
    // On a narrow screen the table scrolls sideways inside this box, never the whole page.
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="text-xs tracking-wider text-muted uppercase">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">
              Course
            </th>
            {STATE_COLUMNS.map((column) => (
              <th key={column} scope="col" className="px-4 py-3 text-right font-medium whitespace-nowrap">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.id}>
              <td className="px-4 py-3">
                <span className="flex flex-wrap items-center gap-2">
                  <Link to={`/courses/${row.id}`} className="font-medium hover:text-accent hover:underline">
                    {row.title}
                  </Link>
                  <CourseStatusBadge status={row.status} />
                </span>
              </td>
              <td className="px-4 py-3 text-right tabular-nums">{row.not_started}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.in_progress}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.completed}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
