import { Link, NavLink } from "react-router";
import { useAuth } from "./AuthProvider";

function linkClass({ isActive }) {
  const base = "inline-flex min-h-11 items-center text-sm";
  return isActive ? `${base} font-semibold text-accent` : `${base} text-muted hover:text-ink`;
}

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-line bg-surface">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2">
        <Link to="/" className="inline-flex min-h-11 items-center font-semibold">
          Course Delivery
        </Link>
        <NavLink to="/" end className={linkClass}>
          Courses
        </NavLink>
        {/* Only learners have enrolments. Hiding the link is presentation: the API still decides. */}
        {user.role === "learner" && (
          <NavLink to="/my-courses" className={linkClass}>
            My courses
          </NavLink>
        )}
        <div className="ml-auto flex items-center gap-4">
          <span className="text-sm">
            {user.full_name} <span className="text-muted capitalize">· {user.role}</span>
          </span>
          <button type="button" onClick={logout} className="btn-secondary">
            Log out
          </button>
        </div>
      </nav>
      {user.role === "instructor" && (
        <p className="border-t border-line px-4 py-2 text-center text-sm text-muted">
          Instructor tools are coming soon. For now you can browse the catalogue.
        </p>
      )}
    </header>
  );
}
