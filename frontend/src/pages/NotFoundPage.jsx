import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <div className="py-12 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-2 text-muted">There is no page at this address.</p>
      <p className="mt-6">
        <Link to="/" className="font-medium text-accent hover:underline">
          Back to courses
        </Link>
      </p>
    </div>
  );
}
