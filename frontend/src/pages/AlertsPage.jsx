import { useEffect, useState } from "react";
import { Link } from "react-router";
import { dismissAlert, listAlerts } from "../api/alerts";
import { useAlertCount } from "../components/AlertCount";
import { Empty, ErrorMessage, Loading } from "../components/States";
import { formatDate } from "../format";

// Learners who started a course and then went quiet for more than 14 days (goal 10). Only instructors get
// the link; for anyone else the server answers 403, shown as the error.
export default function AlertsPage() {
  const { setCount } = useAlertCount();
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);
  const [dismissing, setDismissing] = useState(null); // the row whose Dismiss is waiting for the server
  const [dismissError, setDismissError] = useState(null);

  // Loads the list, and keeps the nav badge in step with it.
  async function load() {
    const result = await listAlerts();
    setAlerts(result);
    setCount(result.length);
  }

  // Once, when the page opens.
  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  // No confirm step: a dismissed alert does no harm, and comes back if the learner stays quiet after their
  // next lesson. Either way the list loads again, since someone else may have changed it meanwhile.
  async function handleDismiss(alert) {
    setDismissing(rowKey(alert));
    setDismissError(null);
    try {
      await dismissAlert(alert.course.id, alert.learner.id);
    } catch (err) {
      // For example the server's 409: "This alert has already been dismissed."
      setDismissError(err.message);
    }
    try {
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDismissing(null);
    }
  }

  let content;
  if (error) {
    content = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (alerts === null) {
    content = <Loading />;
  } else if (alerts.length === 0) {
    content = <Empty title="No alerts. Every learner in progress has completed a lesson in the last 14 days." />;
  } else {
    content = (
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {alerts.map((alert) => (
          <li
            key={rowKey(alert)}
            className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0 wrap-break-word">
              <p className="font-medium">
                {alert.learner.full_name} <span className="font-normal text-muted">{alert.learner.email}</span>
              </p>
              <p className="mt-1 text-sm">
                <Link to={`/courses/${alert.course.id}`} className="font-medium hover:text-accent hover:underline">
                  {alert.course.title}
                </Link>
                <span className="text-muted">
                  {" "}
                  · Quiet for {alert.days_quiet} days, since{" "}
                  <time dateTime={alert.last_activity_at}>{formatDate(alert.last_activity_at)}</time>
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => handleDismiss(alert)}
              disabled={dismissing !== null}
              className="btn-secondary shrink-0"
            >
              {dismissing === rowKey(alert) ? "Dismissing…" : "Dismiss"}
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
        <p className="text-sm text-muted">
          Learners in progress on a published course who haven't completed a lesson for more than 14 days.
          Dismissing an alert hides it for every instructor, until the learner completes another lesson.
        </p>
      </div>
      {dismissError && <ErrorMessage message={dismissError} />}
      {content}
    </div>
  );
}

// A learner has at most one alert per course, so the pair names the row.
function rowKey(alert) {
  return `${alert.course.id}-${alert.learner.id}`;
}
