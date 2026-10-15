import { useId, useState } from "react";
import { CATEGORIES } from "../api/courses";
import { ErrorMessage } from "./States";

// A course's title, description and category, for creating a course and for editing one.
// onSubmit receives the values and returns a promise. If the server refuses, its message shows here.
// The maxLength values match the API's limits; the server still checks every value itself.
export default function CourseForm({ initial, submitLabel, busyLabel, onSubmit, onCancel }) {
  const id = useId(); // keeps the labels' ids unique if two forms are ever on one page
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [category, setCategory] = useState(initial?.category ?? CATEGORIES[0].value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ title, description, category });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor={`${id}-title`} className="block text-sm font-medium">
          Title
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
        <label htmlFor={`${id}-description`} className="block text-sm font-medium">
          Description
        </label>
        <textarea
          id={`${id}-description`}
          name="description"
          required
          maxLength={5000}
          rows={4}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="input mt-1 py-2"
        />
      </div>
      <div>
        <label htmlFor={`${id}-category`} className="block text-sm font-medium">
          Category
        </label>
        <select
          id={`${id}-category`}
          name="category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="input mt-1"
        >
          {CATEGORIES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {error && <ErrorMessage message={error} />}
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? busyLabel : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={saving} className="btn-secondary">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
