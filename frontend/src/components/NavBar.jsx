import { Link, useLocation } from "react-router";
import { useAuth } from "./AuthProvider";

function linkClass(active) {
  const base = "inline-flex min-h-11 items-center text-sm";
  return active ? `${base} font-semibold text-accent` : `${base} text-muted hover:text-ink`;
}

// A nav link that marks itself as the current page, for sight and for screen readers (aria-current).
function NavItem({ to, active, children }) {
  return (
    <Link to={to} aria-current={active ? "page" : undefined} className={linkClass(active)}>
      {children}
    </Link>
  );
}

export default function NavBar() {
  const { user, logout } = useAuth();
  const { pathname, search } = useLocation();
  // "Courses I created" is the course list filtered to this instructor, so both list links lead to "/".
  const onList = pathname === "/";
  const showingMine = onList && new URLSearchParams(search).get("instructor_id") === String(user.id);

  return (
    <header className="border-b border-line bg-surface">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2">
        <Link to="/" className="inline-flex min-h-11 items-center font-semibold">
          Course Delivery
        </Link>
        <NavItem to="/" active={onList && !showingMine}>
          Courses
        </NavItem>
        {/* Each role's own links are presentation only: the API still decides what each person can do. */}
        {user.role === "instructor" && (
          <NavItem to={`/?instructor_id=${user.id}`} active={showingMine}>
            Courses I created
          </NavItem>
        )}
        {user.role === "learner" && (
          <NavItem to="/my-courses" active={pathname === "/my-courses"}>
            My courses
          </NavItem>
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
    </header>
  );
}
