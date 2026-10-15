import { useEffect, useId, useState } from "react";
import { ACTIVITY_PAGE_SIZE, addComment, listActivity } from "../api/activity";
import { CATEGORIES } from "../api/courses";
import { formatDateTime } from "../format";
import { Empty, ErrorMessage, Loading } from "./States";

// A course's activity log, newest first, with a comment box. The server decides what each person gets:
// instructors every entry, learners only the comments (Decision 8). canJoin is false for a learner who
// isn't enrolled: the server refuses them the feed and comments (403, Decision 20), so the page says why
// instead. `changes` goes up after each change made on the course page, and the newest page loads again.
export default function ActivityFeed({ courseId, canJoin, changes }) {
  const [entries, setEntries] = useState(null);
  const [hasOlder, setHasOlder] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [error, setError] = useState(null);
  const [posted, setPosted] = useState(0); // goes up after each new comment, to load the newest page again

  useEffect(() => {
    if (!canJoin) {
      return;
    }
    let ignore = false; // set when a newer load starts, so an older answer can't overwrite it
    setError(null);
    listActivity(courseId)
      .then((page) => {
        if (!ignore) {
          setEntries(page);
          // A page shorter than the page size means nothing older is left.
          setHasOlder(page.length === ACTIVITY_PAGE_SIZE);
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
  }, [courseId, canJoin, changes, posted]);

  async function loadOlder() {
    setLoadingOlder(true);
    setError(null);
    try {
      const page = await listActivity(courseId, entries[entries.length - 1].id);
      setEntries([...entries, ...page]);
      setHasOlder(page.length === ACTIVITY_PAGE_SIZE);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingOlder(false);
    }
  }

  let feed;
  if (error) {
    feed = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (entries === null) {
    feed = <Loading />;
  } else if (entries.length === 0) {
    feed = <Empty title="No comments yet." />;
  } else {
    feed = (
      <ol className="divide-y divide-line rounded-xl border border-line bg-surface px-4">
        {entries.map((entry) => (
          <Entry key={entry.id} entry={entry} />
        ))}
      </ol>
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Activity and comments</h2>
      {canJoin ? (
        <>
          <CommentBox courseId={courseId} onPosted={() => setPosted((count) => count + 1)} />
          {feed}
          {hasOlder && !error && (
            <button type="button" onClick={loadOlder} disabled={loadingOlder} className="btn-secondary">
              {loadingOlder ? "Loading…" : "Load older"}
            </button>
          )}
        </>
      ) : (
        <p className="text-muted">Enrol to join the discussion.</p>
      )}
    </section>
  );
}

function CommentBox({ courseId, onPosted }) {
  const id = useId();
  const [text, setText] = useState("");
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setPosting(true);
    setError(null);
    try {
      await addComment(courseId, text);
      setText("");
      onPosted();
    } catch (err) {
      setError(err.message);
    } finally {
      setPosting(false);
    }
  }

  // maxLength matches the API's limit; the server still checks the text itself.
  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <label htmlFor={id} className="block text-sm font-medium">
        Add a comment
      </label>
      <textarea
        id={id}
        name="comment"
        required
        maxLength={2000}
        rows={3}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="input py-2"
      />
      {error && <ErrorMessage message={error} />}
      <button type="submit" disabled={posting} className="btn-secondary">
        {posting ? "Posting…" : "Post comment"}
      </button>
    </form>
  );
}

// One log entry: who, what in plain words, and when in the viewer's local time. A comment shows its text
// as plain text (Decision 28), and the author is marked when they are an instructor.
function Entry({ entry }) {
  const isComment = entry.action === "commented";
  return (
    <li className="py-4">
      <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
        <span className="font-medium">{entry.actor.full_name}</span>
        {isComment && entry.actor.role === "instructor" && <span className="badge bg-accent/10 text-accent">Instructor</span>}
        {!isComment && <span>{describe(entry)}</span>}
        <time dateTime={entry.created_at} className="text-muted">
          {formatDateTime(entry.created_at)}
        </time>
      </p>
      {isComment && <p className="mt-1 whitespace-pre-wrap wrap-break-word">{entry.details.text}</p>}
    </li>
  );
}

// What a change entry says, from the details the server stored with it.
function describe(entry) {
  const details = entry.details;
  switch (entry.action) {
    case "created":
      return "created the course";
    case "edited":
      return describeCourseEdit(details);
    case "published":
      return "published the course";
    case "archived":
      return "archived the course";
    case "restored":
      return "restored the course";
    case "lesson_added":
      return `added lesson ${details.position}, "${details.title}"`;
    case "lesson_removed":
      return `removed lesson ${details.position}, "${details.title}"`;
    case "lesson_edited":
      return describeLessonEdit(details);
    case "lessons_reordered":
      // The log keeps only lesson ids here, and some may have been removed since, so no order is named.
      return "reordered the lessons";
    default:
      return "made a change";
  }
}

// details is {field: {from, to}} for each field that really changed. A description can be 5,000 characters,
// so it is only named, not quoted.
function describeCourseEdit(details) {
  const parts = [];
  if (details.title) {
    parts.push(`changed the title from "${details.title.from}" to "${details.title.to}"`);
  }
  if (details.category) {
    parts.push(`changed the category from ${categoryLabel(details.category.from)} to ${categoryLabel(details.category.to)}`);
  }
  if (details.description) {
    parts.push("changed the description");
  }
  return parts.join("; ");
}

// details holds the lesson's title after the edit and {field: {from, to}} for what changed.
function describeLessonEdit(details) {
  const parts = [];
  if (details.changes.title) {
    parts.push(`renamed from "${details.changes.title.from}"`);
  }
  if (details.changes.content) {
    parts.push("changed its content");
  }
  return `edited lesson "${details.title}": ${parts.join(", ")}`;
}

function categoryLabel(value) {
  return CATEGORIES.find((category) => category.value === value)?.label ?? value;
}
