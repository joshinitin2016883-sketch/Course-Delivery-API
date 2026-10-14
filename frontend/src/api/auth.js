import { apiRequest } from "./client";

// A wrong password is also a 401: it must show on the form, not sign anyone out.
export function login(email, password) {
  return apiRequest("/auth/login", { method: "POST", body: { email, password }, signOutOn401: false });
}

// Who the saved token belongs to, with their name and role as the server has them now.
export function getMe() {
  return apiRequest("/auth/me");
}
