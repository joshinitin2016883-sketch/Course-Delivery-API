import { useState } from "react";
import { addLesson, editLesson, removeLesson, reorderLessons } from "../api/courses";
import ConfirmButton from "./ConfirmButton";
import LessonForm from "./LessonForm";
import { Empty, ErrorMessage } from "./States";

// The instructor's lessons: move, edit, remove and add. After each change, onChanged asks the server for
// the course again. The page gives this component a new key whenever the server's lessons change, so
// everything here (an unsaved order, an open form) starts afresh from what the server saved.
export default function LessonManager({ course, onChanged }) {
  const lessons = course.lessons; // in the server's order
  const savedOrder = lessons.map((lesson) => lesson.id);
  const byId = new Map(lessons.map((lesson) => [lesson.id, lesson]));

  // The order on screen. Moving a lesson only changes this; Save order sends it in one request.
  const [order, setOrder] = useState(savedOrder);
  const [savingOrder, setSavingOrder] = useState(false);
  const [orderError, setOrderError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [removeError, setRemoveError] = useState(null); // { lessonId, message } for a refused removal
  const orderChanged = order.join() !== savedOrder.join();

  // Swap a lesson with the one above (step -1) or below (step +1).
  function move(index, step) {
    const next = [...order];
    [next[index], next[index + step]] = [next[index + step], next[index]];
    setOrder(next);
  }

  async function saveOrder() {
    setSavingOrder(true);
    setOrderError(null);
    try {
      await reorderLessons(course.id, order);
      await onChanged();
    } catch (err) {
      setOrderError(err.message);
    } finally {
      setSavingOrder(false);
    }
  }

  // LessonForm shows the server's message if these two throw.
  async function saveEdit(lessonId, values) {
    await editLesson(course.id, lessonId, values);
    setEditingId(null);
    await onChanged();
  }

  async function saveNew(values) {
    await addLesson(course.id, values);
    setAdding(false);
    await onChanged();
  }

  async function remove(lessonId) {
    setRemoveError(null);
    try {
      await removeLesson(course.id, lessonId);
      await onChanged();
    } catch (err) {
      // For example: learners have completed it, or it's the last lesson of a published course.
      setRemoveError({ lessonId, message: err.message });
    }
  }

  return (
    <div className="space-y-4">
      {lessons.length === 0 && <Empty title="No lessons yet. Add the first one below." />}

      <ol className="space-y-4">
        {order.map((id, index) => {
          const lesson = byId.get(id);
          return (
            <li key={id} className="rounded-xl border border-line bg-surface p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-medium wrap-break-word">
                  <span className="text-muted tabular-nums">{index + 1}.</span> {lesson.title}
                </h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    aria-label={`Move "${lesson.title}" up`}
                    onClick={() => move(index, -1)}
                    disabled={index === 0 || savingOrder}
                    className="btn-secondary"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label={`Move "${lesson.title}" down`}
                    onClick={() => move(index, 1)}
                    disabled={index === order.length - 1 || savingOrder}
                    className="btn-secondary"
                  >
                    ↓
                  </button>
                  {/* Editing and removing wait until a new order is saved or cancelled. */}
                  {!orderChanged && editingId !== id && (
                    <>
                      <button type="button" onClick={() => setEditingId(id)} className="btn-secondary">
                        Edit
                      </button>
                      <ConfirmButton
                        label="Remove"
                        question={`Remove lesson ${index + 1}, "${lesson.title}"? This can't be undone.`}
                        confirmLabel="Remove"
                        busyLabel="Removing…"
                        onConfirm={() => remove(id)}
                      />
                    </>
                  )}
                </div>
              </div>
              {editingId === id ? (
                <LessonForm
                  initial={lesson}
                  submitLabel="Save lesson"
                  busyLabel="Saving…"
                  onSubmit={(values) => saveEdit(id, values)}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <div className="mt-3 max-w-prose whitespace-pre-wrap wrap-break-word">{lesson.content}</div>
              )}
              {removeError?.lessonId === id && (
                <div className="mt-4">
                  <ErrorMessage message={removeError.message} />
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {orderChanged && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-4">
          <p className="text-sm">The new order isn't saved yet.</p>
          <button type="button" onClick={saveOrder} disabled={savingOrder} className="btn-primary">
            {savingOrder ? "Saving…" : "Save order"}
          </button>
          <button type="button" onClick={() => setOrder(savedOrder)} disabled={savingOrder} className="btn-secondary">
            Cancel
          </button>
        </div>
      )}
      {orderError && (
        // Usually a 409: the lessons changed since this page loaded, so reload and order them again.
        <div className="space-y-3">
          <ErrorMessage message={orderError} />
          <button type="button" onClick={() => window.location.reload()} className="btn-secondary">
            Reload
          </button>
        </div>
      )}

      {!orderChanged &&
        (adding ? (
          <div className="rounded-xl border border-line bg-surface p-6">
            <h3 className="font-medium">New lesson</h3>
            <LessonForm submitLabel="Add lesson" busyLabel="Adding…" onSubmit={saveNew} onCancel={() => setAdding(false)} />
          </div>
        ) : (
          <button type="button" onClick={() => setAdding(true)} className="btn-secondary">
            Add a lesson
          </button>
        ))}
    </div>
  );
}
