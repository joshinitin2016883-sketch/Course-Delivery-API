import { apiRequest } from "./client";

// Every current inactivity alert, the learner who has been quiet the longest first. Instructors only.
export function listAlerts() {
  return apiRequest("/alerts");
}

// Hides a learner's alert on a course for every instructor, until the learner completes another lesson.
export function dismissAlert(courseId, learnerId) {
  return apiRequest("/alerts/dismiss", { method: "POST", body: { course_id: courseId, learner_id: learnerId } });
}
