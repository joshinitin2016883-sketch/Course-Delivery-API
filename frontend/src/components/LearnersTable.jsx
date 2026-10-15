import { useEffect, useState } from "react";
import { downloadProgressCsv, getCourseProgress } from "../api/courses";
import { formatDate } from "../format";
import { Empty, ErrorMessage, Loading } from "./States";
import { ProgressBadge } from "./Status";

const COLUMNS = ["Name", "Email", "State", "Lessons", "Enrolled", "Started", "Completed", "Last activity"];

// Every learner enrolled in the course, as the server lists them (by name), with their progress.
// Instructors only: the server answers anyone else with 403. `changes` goes up after each change made on
// the course page, and the table loads again then, so "X of Y" follows lessons being added or removed.
export default function LearnersTable({ courseId, changes }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  // The sign-in token travels in a header, which a plain link can't send. So the file is fetched like any
  // other request, then handed to the browser to save under the filename the server chose.
  async function handleDownload() {
    setDownloading(true);
    setDownloadError(null);
    try {
      const { blob, filename } = await downloadProgressCsv(courseId);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      // Give the browser a moment to start saving before the file's temporary address is released.
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    let ignore = false; // set when a newer load starts, so an older answer can't overwrite it
    setError(null);
    getCourseProgress(courseId)
      .then((result) => {
        if (!ignore) {
          setRows(result);
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
  }, [courseId, changes]);

  let content;
  if (error) {
    content = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (rows === null) {
    content = <Loading />;
  } else if (rows.length === 0) {
    content = <Empty title="No learners are enrolled yet." />;
  } else {
    content = (
      // On a narrow screen the table scrolls sideways inside this box, never the whole page. "relative"
      // matters: the hidden "Not yet" labels are positioned absolutely, and without it they would belong to
      // the page instead of this box, escape its scrolling and widen the whole page on a phone.
      <div className="relative overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="text-xs tracking-wider text-muted uppercase">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column} scope="col" className="px-4 py-3 font-medium whitespace-nowrap">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((row) => (
              <tr key={row.learner.id}>
                <td className="px-4 py-3 font-medium whitespace-nowrap">{row.learner.full_name}</td>
                <td className="px-4 py-3 text-muted">{row.learner.email}</td>
                <td className="px-4 py-3">
                  <ProgressBadge status={row.status} />
                </td>
                <td className="px-4 py-3 tabular-nums whitespace-nowrap">
                  {row.lessons_done} of {row.lessons_total}
                </td>
                <DateCell iso={row.enrolled_at} />
                <DateCell iso={row.started_at} />
                <DateCell iso={row.completed_at} />
                <DateCell iso={row.last_activity_at} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Enrolled learners</h2>
        <button type="button" onClick={handleDownload} disabled={downloading} className="btn-secondary">
          {downloading ? "Downloading…" : "Download CSV"}
        </button>
      </div>
      {downloadError && <ErrorMessage message={downloadError} />}
      {content}
    </section>
  );
}

// A date in the viewer's own style, or a dash when it hasn't happened yet (screen readers hear "Not yet").
function DateCell({ iso }) {
  return (
    <td className="px-4 py-3 tabular-nums whitespace-nowrap">
      {iso ? (
        <time dateTime={iso}>{formatDate(iso)}</time>
      ) : (
        <>
          <span aria-hidden="true" className="text-muted">
            —
          </span>
          <span className="sr-only">Not yet</span>
        </>
      )}
    </td>
  );
}
