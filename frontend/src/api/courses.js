import { apiRequest } from "./client";

// The same three categories as the API (backend/app/models/course.py), for the filter and the forms.
export const CATEGORIES = [
  { value: "onboarding", label: "Onboarding" },
  { value: "compliance", label: "Compliance" },
  { value: "skills", label: "Skills" },
];

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

// Every new course starts as a draft; the server ignores anything else sent with it.
export function createCourse({ title, description, category }) {
  return apiRequest("/courses", { method: "POST", body: { title, description, category } });
}

// Saves a course's title, description and category; all three are sent every time.
export function updateCourse(courseId, { title, description, category }) {
  return apiRequest(`/courses/${courseId}`, { method: "PUT", body: { title, description, category } });
}

// move is "publish", "archive" or "restore". The server decides which moves are allowed from the
// current status, and answers with the course as it now is.
export function changeStatus(courseId, move) {
  return apiRequest(`/courses/${courseId}/${move}`, { method: "POST" });
}

export function enroll(courseId) {
  return apiRequest(`/courses/${courseId}/enroll`, { method: "POST" });
}

// One course with its lessons in order. The server sends a learner the lessons' content, and their own
// progress (my_progress), only once they are enrolled.
export function getCourse(courseId) {
  return apiRequest(`/courses/${courseId}`);
}

// Answers with the learner's progress in the course after this lesson is marked complete.
export function completeLesson(courseId, lessonId) {
  return apiRequest(`/courses/${courseId}/lessons/${lessonId}/complete`, { method: "POST" });
}

// Every course the learner is enrolled in, newest enrolment first, with their progress in each.
export function listMyCourses() {
  return apiRequest("/me/courses");
}
