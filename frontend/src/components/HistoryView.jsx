import React, { useState, useEffect, useCallback } from "react";
import {
  Calendar,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  FileText,
  RefreshCw,
  Shield,
} from "lucide-react";
import { fetchUserHistory, fetchHistoryDetail, deleteHistoryRecord } from "../services/historyApi";
import { formatDate } from "../utils/formatters";
import HistoryDetailModal from "./HistoryDetailModal";

/**
 * HistoryView: Clean saved document library for authenticated users.
 * Stripped of technical database language.
 */
export default function HistoryView({ onOpenConsentModal }) {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [limit] = useState(5);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected record for details modal
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Record pending deletion confirmation
  const [recordToDelete, setRecordToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadHistory = useCallback(async (targetPage = 1) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchUserHistory(targetPage, limit);
      setRecords(data.items || []);
      setTotal(data.total || 0);
      setPage(data.page || 1);
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      setError(err.message || "Failed to load saved documents.");
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    loadHistory(1);
  }, [loadHistory]);

  // Handle ESC key for delete confirmation dialog
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && recordToDelete && !isDeleting) {
        setRecordToDelete(null);
      }
    };
    if (recordToDelete) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [recordToDelete, isDeleting]);

  const handleViewDetail = async (recordId) => {
    setIsDetailLoading(true);
    try {
      const detail = await fetchHistoryDetail(recordId);
      setSelectedRecord(detail);
      setIsDetailModalOpen(true);
    } catch (err) {
      setError(err.message || "Could not retrieve document details.");
    } finally {
      setIsDetailLoading(false);
    }
  };

  const confirmDelete = (recordId) => {
    setRecordToDelete(recordId);
  };

  const handleDeleteConfirmed = async () => {
    if (!recordToDelete) return;
    setIsDeleting(true);
    try {
      await deleteHistoryRecord(recordToDelete);
      if (selectedRecord && selectedRecord.id === recordToDelete) {
        setIsDetailModalOpen(false);
        setSelectedRecord(null);
      }
      setRecordToDelete(null);
      const nextPage = records.length === 1 && page > 1 ? page - 1 : page;
      await loadHistory(nextPage);
    } catch (err) {
      setError(err.message || "Failed to delete document.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className="history-section">
      {/* Header */}
      <div className="history-header">
        <div>
          <h2>Saved Documents</h2>
          <p className="history-subtitle">
            Review your previously saved healthcare documents and highlighted information.
          </p>
        </div>

        <div className="history-header-actions">
          <button
            type="button"
            className="btn btn-outline-sm"
            onClick={() => loadHistory(page)}
            disabled={isLoading}
            title="Refresh document list"
          >
            <RefreshCw size={13} className={isLoading ? "spin-icon" : ""} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            className="btn btn-outline-sm"
            onClick={onOpenConsentModal}
            title="View privacy terms"
          >
            <Shield size={13} />
            <span>Privacy Terms</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: "1.25rem" }}>
          <AlertCircle size={18} />
          <span>{error}</span>
          <button
            type="button"
            className="link-btn"
            style={{ marginLeft: "auto", fontSize: "0.85rem" }}
            onClick={() => loadHistory(page)}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="history-loading-box">
          <RefreshCw size={24} className="spin-icon" style={{ color: "var(--primary)" }} />
          <span>Loading your saved documents...</span>
        </div>
      ) : records.length === 0 ? (
        /* Empty State */
        <div className="empty-history-card">
          <div className="empty-history-icon">
            <FileText size={40} style={{ color: "#94a3b8" }} />
          </div>
          <h3>No Saved Documents Yet</h3>
          <p>
            When you extract information from a document while signed in, click "Save Document" to keep it here for future reference.
          </p>
        </div>
      ) : (
        /* Records List */
        <div className="history-list">
          {records.map((rec) => (
            <div key={rec.id} className="history-card">
              <div className="history-card-header">
                <div className="history-card-date">
                  <Calendar size={14} style={{ color: "var(--primary)" }} />
                  <span>{formatDate(rec.created_at)}</span>
                </div>
                <div className="history-card-actions">
                  <button
                    type="button"
                    className="btn-history-action btn-view"
                    onClick={() => handleViewDetail(rec.id)}
                    disabled={isDetailLoading}
                    title="View original document and highlighted information"
                  >
                    <Eye size={14} />
                    <span>View Details</span>
                  </button>
                  <button
                    type="button"
                    className="btn-history-action btn-delete"
                    onClick={() => confirmDelete(rec.id)}
                    title="Delete document"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="history-card-body">
                <p className="history-preview-text">
                  "{rec.form_text_preview}"
                </p>
              </div>

              <div className="history-card-footer">
                <div className="history-entity-pills">
                  {rec.entity_counts?.MEDICATION ? (
                    <span className="history-pill pill-med">
                      {rec.entity_counts.MEDICATION} Medication{rec.entity_counts.MEDICATION > 1 ? "s" : ""}
                    </span>
                  ) : null}
                  {rec.entity_counts?.DATE ? (
                    <span className="history-pill pill-date">
                      {rec.entity_counts.DATE} Date{rec.entity_counts.DATE > 1 ? "s" : ""}
                    </span>
                  ) : null}
                  {rec.entity_counts?.CONDITION ? (
                    <span className="history-pill pill-cond">
                      {rec.entity_counts.CONDITION} Condition{rec.entity_counts.CONDITION > 1 ? "s" : ""}
                    </span>
                  ) : null}
                  {rec.total_entities === 0 && (
                    <span className="history-pill" style={{ background: "var(--border-subtle)", color: "var(--text-muted)" }}>
                      No items
                    </span>
                  )}
                </div>
                <span className="history-total-count">
                  {rec.total_entities} {rec.total_entities === 1 ? "item" : "items"} found
                </span>
              </div>
            </div>
          ))}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="pagination-bar">
              <button
                type="button"
                className="btn btn-outline-sm"
                onClick={() => loadHistory(page - 1)}
                disabled={page <= 1 || isLoading}
              >
                <ChevronLeft size={16} />
                <span>Previous</span>
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages} ({total} documents)
              </span>
              <button
                type="button"
                className="btn btn-outline-sm"
                onClick={() => loadHistory(page + 1)}
                disabled={page >= totalPages || isLoading}
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Details Modal */}
      <HistoryDetailModal
        isOpen={isDetailModalOpen}
        record={selectedRecord}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedRecord(null);
        }}
        onDelete={(id) => {
          setIsDetailModalOpen(false);
          confirmDelete(id);
        }}
      />

      {/* Delete Confirmation Dialog */}
      {recordToDelete && (
        <div className="modal-overlay" onClick={() => !isDeleting && setRecordToDelete(null)}>
          <div className="modal-card confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <div className="modal-icon-badge badge-danger">
                  <Trash2 size={20} />
                </div>
                <div>
                  <h2>Delete Saved Document?</h2>
                  <p className="modal-subtitle">
                    This document will be removed from your saved list.
                  </p>
                </div>
              </div>
            </div>
            <div className="modal-body" style={{ padding: "1rem 1.5rem" }}>
              <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
                Are you sure you want to delete this saved healthcare document? The text and highlighted information will be permanently removed.
              </p>
            </div>
            <div className="modal-actions" style={{ padding: "1rem 1.5rem", display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={isDeleting}
                onClick={() => setRecordToDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={isDeleting}
                onClick={handleDeleteConfirmed}
              >
                {isDeleting ? "Deleting..." : "Yes, Delete Document"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
