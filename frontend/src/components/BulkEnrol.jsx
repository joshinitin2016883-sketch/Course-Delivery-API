import { useId, useState } from "react";
import { bulkEnroll } from "../api/courses";
import { ErrorMessage } from "./States";

// Each outcome the server reports, in plain words.
const OUTCOMES = [
  { key: "enrolled", label: "Enrolled now" },
  { key: "already_enrolled", label: "Already enrolled" },
  { key: "unknown", label: "No account with this address" },
  { key: "invalid", label: "Not an email address" },
  { key: "not_a_learner", label: "Instructor account, not enrolled" },
];
const OUTCOME_LABELS = Object.fromEntries(OUTCOMES.map(({ key, label }) => [key, label]));

// The instructor's "Enrol learners" section (goal 7). Paste addresses, or load a .csv or .txt file into the
// box so you see exactly what will be sent; the server does all the splitting and checking. Only a published
// course takes new learners (Decision 18), so on a draft or archived course this only says why; the server
// refuses those too (409). onEnrolled lets the page reload its Enrolled learners table.
export default function BulkEnrol({ course, onEnrolled }) {
  const id = useId();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (course.status !== "published") {
    return (
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Enrol learners</h2>
        <p className="text-muted">
          Only a published course can take new learners. {course.status === "draft" ? "Publish" : "Restore"} this one
          first.
        </p>
      </section>
    );
  }

  // Reads the chosen file here in the browser and puts its text in the box. Nothing is sent yet.
  async function handleFile(event) {
    const file = event.target.files[0];
    if (file) {
      setText(await file.text());
    }
    event.target.value = ""; // so choosing the same file again still counts as a change
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSending(true);
    setError(null);
    setResult(null);
    try {
      setResult(await bulkEnroll(course.id, text));
      setText("");
      onEnrolled();
    } catch (err) {
      // The server's reason, such as "Paste at least one email address." or a 409 if the course was archived.
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Enrol learners</h2>
      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-line bg-surface p-6">
        <div>
          <label htmlFor={`${id}-addresses`} className="block text-sm font-medium">
            Email addresses
          </label>
          <p id={`${id}-hint`} className="text-sm text-muted">
            Separate them with commas, spaces or new lines, or load them from a file below.
          </p>
          <textarea
            id={`${id}-addresses`}
            name="addresses"
            aria-describedby={`${id}-hint`}
            required
            maxLength={200000}
            rows={5}
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="input mt-2 py-2"
          />
        </div>
        <div>
          <label htmlFor={`${id}-file`} className="block text-sm font-medium">
            Load a .csv or .txt file
          </label>
          <input
            id={`${id}-file`}
            name="file"
            type="file"
            accept=".csv,.txt,text/csv,text/plain"
            onChange={handleFile}
            className="mt-2 block text-sm file:mr-3 file:min-h-11 file:rounded-lg file:border file:border-line file:bg-surface file:px-4 file:text-sm file:font-medium file:text-ink"
          />
        </div>
        {error && <ErrorMessage message={error} />}
        <button type="submit" disabled={sending} className="btn-secondary">
          {sending ? "Enrolling…" : "Enrol these learners"}
        </button>
      </form>

      {/* aria-live: a screen reader hears the totals when the result arrives. */}
      <div aria-live="polite">
        {result && (
          <div className="space-y-3">
            <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {OUTCOMES.map(({ key, label }) => (
                <li key={key}>
                  {label}: <span className="font-medium tabular-nums">{result.counts[key]}</span>
                </li>
              ))}
              <li>
                Repeats removed: <span className="font-medium tabular-nums">{result.repeats_removed}</span>
              </li>
            </ul>
            <div className="relative overflow-x-auto rounded-xl border border-line bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="text-xs tracking-wider text-muted uppercase">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Address
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Result
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {result.results.map((row) => (
                    <tr key={row.email}>
                      <td className="px-4 py-3 wrap-anywhere">{row.email}</td>
                      <td className="px-4 py-3">{OUTCOME_LABELS[row.outcome]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
