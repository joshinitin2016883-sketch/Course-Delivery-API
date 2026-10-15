import { useId, useState } from "react";
import { ErrorMessage } from "./States";

// A lesson's title and content, for adding a lesson and for editing one. The content is plain text: its
// line breaks are kept and any HTML shows as typed (Decision 28). The maxLength values match the API's
// limits; the server still checks every value itself, and its message shows here if it refuses.
export default function LessonForm({ initial, submitLabel, busyLabel, onSubmit, onCancel }) {
  const id = useId(); // keeps the labels' ids unique: several lesson forms can be open on one page
  const [title, setTitle] = useState(initial?.title ?? "");
  const [content, setContent] = useState(initial?.content ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ title, content });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-4">
      <div>
        <label htmlFor={`${id}-title`} className="block text-sm font-medium">
          Lesson title
        </label>
        <input
          id={`${id}-title`}
          name="title"
          required
          maxLength={200}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="input mt-1"
        />
      </div>
      <div>
        <label htmlFor={`${id}-content`} className="block text-sm font-medium">
          Content
        </label>
        <textarea
          id={`${id}-content`}
          name="content"
          required
          maxLength={20000}
          rows={8}
          value={content}
          onChange={(event) => setContent(event.target.value)}
          className="input mt-1 py-2"
        />
      </div>
      {error && <ErrorMessage message={error} />}
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? busyLabel : submitLabel}
        </button>
        <button type="button" onClick={onCancel} disabled={saving} className="btn-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
}
