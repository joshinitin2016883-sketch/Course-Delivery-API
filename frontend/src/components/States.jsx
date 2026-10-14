// The loading, empty and error states, shared so every page shows them the same way.

export function Loading() {
  return (
    <div role="status" className="space-y-3">
      <span className="sr-only">Loading…</span>
      <div className="h-20 rounded-xl bg-line motion-safe:animate-pulse" />
      <div className="h-20 rounded-xl bg-line motion-safe:animate-pulse" />
      <div className="h-20 rounded-xl bg-line motion-safe:animate-pulse" />
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-6 py-12 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
  );
}

// onRetry is optional: pass it when trying again could help, such as a page that failed to load.
export function ErrorMessage({ message, onRetry }) {
  return (
    <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-3">
          Try again
        </button>
      )}
    </div>
  );
}
