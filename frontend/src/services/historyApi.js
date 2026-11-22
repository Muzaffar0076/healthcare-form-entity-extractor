/**
 * API client service for User Extraction History.
 *
 * Provides authenticated CRUD operations for saving, retrieving,
 * and deleting user healthcare form extraction records.
 */

import { ensureCsrfToken } from "./authApi";
import { API_BASE } from "./apiConfig";

/**
 * Save an extraction record to the authenticated user's history.
 * @param {Object} payload - { form_text: string, extracted_entities: { entities: Array } }
 * @returns {Promise<Object>} Created history record
 */
export async function saveExtractionHistory(payload) {
  let csrfToken = await ensureCsrfToken();
  let response = await fetch(`${API_BASE}/api/v1/history`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
  });

  // Self-healing: if rejected due to stale CSRF token, force-fetch fresh token and retry once
  if (response.status === 403) {
    const errData = await response.clone().json().catch(() => ({}));
    if (errData.message && errData.message.toLowerCase().includes("csrf")) {
      try {
        csrfToken = await ensureCsrfToken(true);
        response = await fetch(`${API_BASE}/api/v1/history`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify(payload),
        });
      } catch {
        // Keep original response
      }
    }
  }

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || result.detail || `Failed to save extraction (${response.status})`);
  }
  return result;
}

/**
 * Fetch paginated extraction history for the current user.
 * @param {number} page - Page number (1-indexed)
 * @param {number} limit - Items per page
 * @returns {Promise<Object>} { items, total, page, limit, total_pages }
 */
export async function fetchUserHistory(page = 1, limit = 5) {
  const response = await fetch(`${API_BASE}/api/v1/history?page=${page}&limit=${limit}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || result.detail || `Failed to fetch history (${response.status})`);
  }
  return result;
}

/**
 * Fetch a single extraction history record by ID.
 * @param {string} recordId
 * @returns {Promise<Object>} Detailed history record
 */
export async function fetchHistoryDetail(recordId) {
  const response = await fetch(`${API_BASE}/api/v1/history/${recordId}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || result.detail || `Failed to load record (${response.status})`);
  }
  return result;
}

/**
 * Delete a specific extraction history record.
 * @param {string} recordId
 * @returns {Promise<Object>}
 */
export async function deleteHistoryRecord(recordId) {
  let csrfToken = await ensureCsrfToken();
  let response = await fetch(`${API_BASE}/api/v1/history/${recordId}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
  });

  // Self-healing: if rejected due to stale CSRF token, force-fetch fresh token and retry once
  if (response.status === 403) {
    const errData = await response.clone().json().catch(() => ({}));
    if (errData.message && errData.message.toLowerCase().includes("csrf")) {
      try {
        csrfToken = await ensureCsrfToken(true);
        response = await fetch(`${API_BASE}/api/v1/history/${recordId}`, {
          method: "DELETE",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
        });
      } catch {
        // Keep original response
      }
    }
  }

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || result.detail || `Failed to delete record (${response.status})`);
  }
  return result;
}

