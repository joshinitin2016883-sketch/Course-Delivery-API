// Every API call goes through send(), by way of apiRequest (JSON) or apiDownload (files). It adds the sign-in
// token, turns an error response into an ApiError carrying the server's message, signs the user out on a 401,
// and reports slow requests.

const API_URL = import.meta.env.VITE_API_URL;
if (!API_URL) {
  throw new Error("VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env.local.");
}

const TOKEN_KEY = "token";
const SLOW_AFTER_MS = 3000;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status; // 0 when no response arrived at all
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// AuthProvider sets this: it forgets the user and goes to /login.
let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

// WakingBanner sets this: it is told true while any request is slow, and false once none are.
let onSlowChange = () => {};
let slowRequests = 0;

export function setSlowRequestHandler(handler) {
  onSlowChange = handler;
}

function countSlow(change) {
  slowRequests += change;
  onSlowChange(slowRequests > 0);
}

// Sends one request and returns the response once it has arrived and is OK. What every call needs happens here:
// the token, the slow-request banner, signing out on a 401, and turning an error response into ApiError.
// signOutOn401 is false only for the login call, where a 401 means a wrong password, not an old token.
async function send(path, { method = "GET", body, signOutOn401 = true } = {}) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let slow = false;
  const slowTimer = setTimeout(() => {
    slow = true;
    countSlow(1);
  }, SLOW_AFTER_MS);

  let response;
  try {
    response = await fetch(API_URL + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only fails like this when no response arrived: offline, or the API refused us by CORS.
    throw new ApiError(0, "Couldn't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(slowTimer);
    if (slow) {
      countSlow(-1);
    }
  }

  if (response.status === 401 && signOutOn401) {
    clearToken();
    onUnauthorized();
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return response;
}

// For the API's JSON answers.
export async function apiRequest(path, options) {
  const response = await send(path, options);
  // 204 No Content (removing a lesson) has no body to read.
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

// For a file the API sends, such as the progress CSV: its contents, and the filename the server chose. The
// filename comes from Content-Disposition, which the API exposes to other origins for exactly this.
export async function apiDownload(path) {
  const response = await send(path);
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "download";
  return { blob: await response.blob(), filename };
}

// FastAPI puts the reason in "detail": a sentence for the API's own errors,
// or a list of problems for a 422 validation error, where the first one is shown.
async function readErrorMessage(response) {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail[0].msg;
    }
  } catch {
    // The body wasn't JSON, for example an error page from Render's proxy.
  }
  return `Something went wrong (error ${response.status}). Please try again.`;
}
