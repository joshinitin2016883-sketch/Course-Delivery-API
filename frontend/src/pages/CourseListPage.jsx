import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { CATEGORIES, enroll, listCourses, listInstructors } from "../api/courses";
import { useAuth } from "../components/AuthProvider";
import Pagination from "../components/Pagination";
import { Empty, ErrorMessage, Loading } from "../components/States";
import { CourseStatusBadge } from "../components/Status";

// The three course states, for the instructors' status filter.
const STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

// One dropdown sets two of the API's parameters at once: sort and order.
const SORT_OPTIONS = [
  { value: "created_at:desc", label: "Newest first" },
  { value: "created_at:asc", label: "Oldest first" },
  { value: "title:asc", label: "Title A–Z" },
  { value: "title:desc", label: "Title Z–A" },
  { value: "enrollment_count:desc", label: "Most enrolled" },
  { value: "enrollment_count:asc", label: "Fewest enrolled" },
];

const SEARCH_DELAY_MS = 300;

export default function CourseListPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  // The search, filters, sort and page live in the URL, so a reload, Back or a shared link shows the same list.
  const q = searchParams.get("q") ?? "";
  const category = searchParams.get("category") ?? "";
  const status = searchParams.get("status") ?? "";
  const instructorId = searchParams.get("instructor_id") ?? "";
  const sort = searchParams.get("sort") ?? "created_at";
  const order = searchParams.get("order") ?? "desc";
  const page = searchParams.get("page") ?? "1";

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // The names for the instructor filter. Until they arrive it offers only "All instructors".
  const [instructors, setInstructors] = useState([]);
  const [instructorsError, setInstructorsError] = useState(null);

  // The text in the search box. It changes as you type, and reaches the URL once typing pauses.
  const [searchText, setSearchText] = useState(q);
  // If the URL's search changes some other way (Back or Forward), copy it into the box.
  const [copiedQ, setCopiedQ] = useState(q);
  if (q !== copiedQ) {
    setCopiedQ(q);
    setSearchText(q);
  }

  // Writes new values into the URL. A new search, filter or sort always starts again from page 1.
  function changeFilters(changes) {
    const next = new URLSearchParams(searchParams);
    for (const [name, value] of Object.entries(changes)) {
      if (value) {
        next.set(name, value);
      } else {
        next.delete(name);
      }
    }
    next.delete("page");
    setSearchParams(next);
  }

  function goToPage(number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(number));
    setSearchParams(next);
  }

  // The debounce. Each keystroke restarts the timer, so the search is sent once typing pauses.
  // Any other URL change restarts it too, so it always builds on the current filters.
  useEffect(() => {
    if (searchText === q) {
      return;
    }
    const timer = setTimeout(() => changeFilters({ q: searchText }), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchText, searchParams]);

  // Load the instructors' names once, for the instructor filter.
  useEffect(() => {
    listInstructors()
      .then(setInstructors)
      .catch((err) => setInstructorsError(err.message));
  }, []);

  // Load the page of courses the URL describes.
  useEffect(() => {
    let ignore = false; // set when the URL changes again, so a slower, older answer can't overwrite a newer one
    setLoading(true);
    setError(null);
    listCourses({ q, category, status, instructorId, sort, order, page })
      .then((result) => {
        if (!ignore) {
          setData(result);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [q, category, status, instructorId, sort, order, page]);

  // The server has accepted an enrolment: show it in that row without reloading the list.
  function markEnrolled(courseId) {
    setData((current) => ({
      ...current,
      items: current.items.map((course) =>
        course.id === courseId ? { ...course, enrolled: true, enrollment_count: course.enrollment_count + 1 } : course,
      ),
    }));
  }

  const hasFilters = q.trim() !== "" || category !== "" || status !== "" || instructorId !== "";

  // While a new answer loads, the old rows stay on screen, dimmed through aria-busy.
  let results;
  if (error) {
    results = <ErrorMessage message={error} onRetry={() => window.location.reload()} />;
  } else if (data === null) {
    results = <Loading />;
  } else if (data.items.length === 0) {
    results = (
      <Empty title={emptyTitle(data.total, hasFilters)}>
        {hasFilters && (
          <button
            type="button"
            onClick={() => changeFilters({ q: "", category: "", status: "", instructor_id: "" })}
            className="btn-secondary mt-2"
          >
            Clear search and filters
          </button>
        )}
      </Empty>
    );
  } else {
    results = (
      <ul aria-busy={loading} className="divide-y divide-line rounded-xl border border-line bg-surface aria-busy:opacity-60">
        {data.items.map((course) => (
          <CourseRow key={course.id} course={course} canEnroll={user.role === "learner"} onEnrolled={markEnrolled} />
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* "Courses I created" in the nav is this list filtered to the instructor's own id. */}
        <h1 className="text-2xl font-semibold tracking-tight">
          {user.role === "instructor" && instructorId === String(user.id) ? "Courses I created" : "Courses"}
        </h1>
        {/* Only instructors create courses. Hiding the button is presentation: the server refuses anyone else. */}
        {user.role === "instructor" && (
          <Link to="/courses/new" className="btn-primary">
            New course
          </Link>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="search" className="block text-sm font-medium">
            Search
          </label>
          <input
            id="search"
            type="search"
            placeholder="Titles and descriptions"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            className="input mt-1"
          />
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
          <FilterSelect id="category" label="Category" value={category} onChange={(value) => changeFilters({ category: value })}>
            <option value="">All categories</option>
            {CATEGORIES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </FilterSelect>

          {/* Only instructors can see drafts and archived courses, so only they get this filter.
              Hiding it is presentation: the server limits learners to published courses anyway. */}
          {user.role === "instructor" && (
            <FilterSelect id="status" label="Status" value={status} onChange={(value) => changeFilters({ status: value })}>
              <option value="">All statuses</option>
              {STATUSES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FilterSelect>
          )}

          <FilterSelect
            id="instructor"
            label="Instructor"
            value={instructorId}
            onChange={(value) => changeFilters({ instructor_id: value })}
          >
            <option value="">All instructors</option>
            {instructors.map((instructor) => (
              <option key={instructor.id} value={String(instructor.id)}>
                {instructor.full_name}
              </option>
            ))}
          </FilterSelect>

          <FilterSelect
            id="sort"
            label="Sort by"
            value={`${sort}:${order}`}
            onChange={(value) => {
              const [newSort, newOrder] = value.split(":");
              changeFilters({ sort: newSort, order: newOrder });
            }}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </FilterSelect>
        </div>

        {instructorsError && (
          <p className="text-sm text-danger">Couldn't load the instructors for the filter: {instructorsError}</p>
        )}
      </div>

      {results}

      {!error && data !== null && data.total > 0 && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onPageChange={goToPage}
          disabled={loading}
        />
      )}
    </div>
  );
}

// A labelled dropdown in the row of filters.
function FilterSelect({ id, label, value, onChange, children }) {
  return (
    <div className="sm:min-w-40 sm:flex-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className="input mt-1">
        {children}
      </select>
    </div>
  );
}

function emptyTitle(total, hasFilters) {
  // Matches exist, just not on this page: for example ?page=9 on a list with fewer pages.
  if (total > 0) {
    return "There are no courses on this page.";
  }
  return hasFilters ? "No courses match your search and filters." : "No courses yet.";
}

// One course in the list. Each row has its own Enrol button, disabled only while its own request runs.
function CourseRow({ course, canEnroll, onEnrolled }) {
  const [enrolling, setEnrolling] = useState(false);
  const [error, setError] = useState(null);

  async function handleEnroll() {
    setEnrolling(true);
    setError(null);
    try {
      await enroll(course.id);
      onEnrolled(course.id);
    } catch (err) {
      // The server's reason, such as "You are already enrolled in this course."
      setError(err.message);
    } finally {
      setEnrolling(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 wrap-break-word">
        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/courses/${course.id}`} className="font-medium hover:text-accent hover:underline">
            {course.title}
          </Link>
          {/* Only instructors get draft or archived courses here; learners only ever see published ones. */}
          <CourseStatusBadge status={course.status} />
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-muted">{course.description}</p>
        <p className="mt-1 text-sm text-muted">
          <span className="capitalize">{course.category}</span> · {course.instructor.full_name} ·{" "}
          <span className="tabular-nums">{course.enrollment_count}</span> enrolled
        </p>
      </div>
      <div className="shrink-0">
        {course.enrolled && <span className="badge bg-success/10 text-success">Enrolled</span>}
        {/* Hiding Enrol from instructors is presentation only: the API refuses them anyway (403). */}
        {canEnroll && !course.enrolled && (
          <button type="button" onClick={handleEnroll} disabled={enrolling} className="btn-secondary">
            {enrolling ? "Enrolling…" : "Enrol"}
          </button>
        )}
        {error && (
          <p role="alert" className="mt-2 max-w-xs text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </li>
  );
}
