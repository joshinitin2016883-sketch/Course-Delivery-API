import { apiRequest } from "./client";

// One page of the course list. Searching, filtering, sorting and paging all happen on the server.
export function listCourses({ q, category, status, instructorId, sort, order, page }) {
  const params = new URLSearchParams({ sort, order, page });
  // The search and the filters are only sent when they have a value.
  const optional = { q, category, status, instructor_id: instructorId };
  for (const [name, value] of Object.entries(optional)) {
    if (value) {
      params.set(name, value);
    }
  }
  return apiRequest(`/courses?${params}`);
}

// The names the instructor filter offers: id and full name for every instructor.
export function listInstructors() {
  return apiRequest("/instructors");
}

export function enroll(courseId) {
  return apiRequest(`/courses/${courseId}/enroll`, { method: "POST" });
}
