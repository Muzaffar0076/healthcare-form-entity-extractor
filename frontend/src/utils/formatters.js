/**
 * Shared utility functions for formatting dates, file sizes, and clinical confidence scores.
 */

/**
 * Format an ISO timestamp into a human-readable date and time.
 * @param {string|Date|null} isoString
 * @returns {string}
 */
export function formatDate(isoString) {
  if (!isoString) return "Unknown date";
  try {
    return new Date(isoString).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Invalid date";
  }
}

/**
 * Format bytes into human-readable B, KB, or MB.
 * @param {number} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (typeof bytes !== "number" || isNaN(bytes)) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Format model confidence score into a patient-friendly badge.
 * @param {number|null} confidence
 * @returns {{ label: string, level: string, percentage: string }}
 */
export function getConfidenceInfo(confidence) {
  if (confidence === null || confidence === undefined || isNaN(confidence)) {
    return { label: "Extracted", level: "neutral", percentage: "" };
  }
  const pct = Math.round(confidence * 100);
  if (pct >= 85) {
    return { label: "High Confidence", level: "high", percentage: `${pct}%` };
  }
  if (pct >= 65) {
    return { label: "Probable Match", level: "medium", percentage: `${pct}%` };
  }
  return { label: "Review Recommended", level: "low", percentage: `${pct}%` };
}

