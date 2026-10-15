import { useState } from "react";

// A button that asks once more, on the page itself, before doing something hard to undo.
// The first click shows the question with two buttons; only the second click runs onConfirm.
// onConfirm handles its own errors (it shows the server's message), so this only waits for it.
export default function ConfirmButton({ label, question, confirmLabel, busyLabel, onConfirm }) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    setBusy(true);
    await onConfirm();
    setBusy(false);
    setAsking(false);
  }

  if (!asking) {
    return (
      <button type="button" onClick={() => setAsking(true)} className="btn-secondary">
        {label}
      </button>
    );
  }

  // Cancel takes the focus, so pressing Enter straight away is the safe choice.
  return (
    <div role="group" aria-label={question} className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-page p-3">
      <span className="text-sm">{question}</span>
      <button type="button" onClick={handleConfirm} disabled={busy} className="btn-primary">
        {busy ? busyLabel : confirmLabel}
      </button>
      <button type="button" onClick={() => setAsking(false)} disabled={busy} autoFocus className="btn-secondary">
        Cancel
      </button>
    </div>
  );
}
