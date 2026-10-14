// Page controls for the course list, which the server splits into pages:
// which page this is, how many courses match in all, and Previous / Next.
export default function Pagination({ page, pageSize, total, onPageChange, disabled }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-4">
      <p aria-live="polite" className="text-sm text-muted tabular-nums">
        Page {page} of {pageCount} · {total} {total === 1 ? "course" : "courses"}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={disabled || page <= 1}
          className="btn-secondary"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={disabled || page >= pageCount}
          className="btn-secondary"
        >
          Next
        </button>
      </div>
    </nav>
  );
}
