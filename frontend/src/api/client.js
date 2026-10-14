// Every API call goes through apiRequest. It adds the sign-in token, turns an error response into an
// ApiError carrying the server's message, signs the user out on a 401, and reports slow requests.

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

// signOutOn401 is false only for the login call, where a 401 means a wrong password, not an old token.
export async function apiRequest(path, { method = "GET", body, signOutOn401 = true } = {}) {
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

  return response.json();
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
