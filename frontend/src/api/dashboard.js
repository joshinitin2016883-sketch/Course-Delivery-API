import { apiRequest } from "./client";

// The instructors' dashboard: headline numbers, enrolments by course and state, and completions per week.
export function getDashboard() {
  return apiRequest("/dashboard");
}
