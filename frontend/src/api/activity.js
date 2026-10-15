import { apiRequest } from "./client";

export const ACTIVITY_PAGE_SIZE = 20;

// One page of a course's activity log, newest first. To get older entries, pass the id of the last entry
// received as `before`. Instructors get every entry; learners only the comments (Decision 8).
export function listActivity(courseId, before) {
  const params = new URLSearchParams({ limit: ACTIVITY_PAGE_SIZE });
  if (before) {
    params.set("before", before);
  }
  return apiRequest(`/courses/${courseId}/activity?${params}`);
}

export function addComment(courseId, text) {
  return apiRequest(`/courses/${courseId}/comments`, { method: "POST", body: { text } });
}
