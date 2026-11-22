/**
 * API client service for Authentication & User management.
 *
 * Implements SEC-05:
 * - Credentials: "include" for HttpOnly cookie session management.
 * - CSRF token retrieval and X-CSRF-Token header attachment on state-changing requests.
 * - Complete removal of raw JWT token handling in client JavaScript.
 */

const API_BASE = "http://localhost:8000";

/**
 * Retrieve CSRF token from browser cookies if present and structurally valid.
 * Discards expired tokens (> 23 hours old) or malformed strings.
 * @returns {string|null}
 */
export function getCsrfTokenFromCookie() {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(^|;\s*)csrf_token=([^;]+)/);
  if (!match) return null;

  const token = decodeURIComponent(match[2]);
  const parts = token.split(":");
  if (parts.length !== 4) {
    return null;
  }

  const ts = parseInt(parts[0], 10);
  const now = Math.floor(Date.now() / 1000);
  // Max age is 24 hours (86400s). Discard client-side if older than 23 hours or future-dated.
  if (isNaN(ts) || now - ts > 23 * 3600 || ts > now + 5) {
    return null;
  }

  return token;
}

/**
 * Fetch a fresh CSRF token from the server.
 * Sets the csrf_token cookie on the browser and returns the token string.
 * @returns {Promise<string>}
 */
export async function fetchCsrfToken() {
  const response = await fetch(`${API_BASE}/api/auth/csrf-token`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error("Failed to initialize security tokens.");
  }
  const data = await response.json();
  return data.csrfToken;
}

/**
 * Get or fetch an active CSRF token.
 * If forceFresh is true or the cookie token is missing/expired, fetches a fresh token from the server.
 * @param {boolean} [forceFresh=false]
 * @returns {Promise<string>}
 */
export async function ensureCsrfToken(forceFresh = false) {
  let token = forceFresh ? null : getCsrfTokenFromCookie();
  if (!token) {
    token = await fetchCsrfToken();
  }
  return token;
}

/**
 * Register a new user account.
 * Always fetches a fresh CSRF token before submission to guarantee validity and session binding.
 * Sets HttpOnly access_token cookie automatically via response.
 * @param {Object} data - { fullName, email, password, confirmPassword, phoneNumber }
 * @returns {Promise<Object>}
 */
export async function registerUser(data) {
  const csrfToken = await fetchCsrfToken();
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || `Registration failed (${response.status})`);
  }
  return result;
}

/**
 * Authenticate an existing user.
 * Always fetches a fresh CSRF token before submission to guarantee validity and session binding.
 * Sets HttpOnly access_token cookie automatically via response.
 * @param {Object} data - { email, password }
 * @returns {Promise<Object>}
 */
export async function loginUser(data) {
  const csrfToken = await fetchCsrfToken();
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || `Login failed (${response.status})`);
  }
  return result;
}

/**
 * Retrieve the current authenticated user's profile using the HttpOnly cookie.
 * @returns {Promise<Object>} User profile
 */
export async function getCurrentUser() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || `Session verification failed (${response.status})`);
  }
  return result;
}

/**
 * Log out active session: clears cookies and revokes server-side session.
 * Always fetches a fresh CSRF token bound to the current session before sending logout request.
 * @returns {Promise<Object>}
 */
export async function logoutUser() {
  const csrfToken = await fetchCsrfToken();
  const response = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || `Logout failed (${response.status})`);
  }
  return result;
}
