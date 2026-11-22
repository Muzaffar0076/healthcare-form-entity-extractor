import React, { useEffect, useRef } from "react";
import { ShieldCheck, AlertTriangle, X, Check, Lock } from "lucide-react";

export default function ConsentModal({ isOpen, onClose, onConfirm }) {
  const confirmBtnRef = useRef(null);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      // Auto-focus the primary confirmation button when opened
      setTimeout(() => confirmBtnRef.current?.focus(), 50);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card consent-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-title"
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge badge-success">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2 id="consent-title">Consent to Store Extraction History</h2>
              <p className="modal-subtitle">
                Please review our data storage and privacy practices before enabling history.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close consent dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body consent-body">
          <div className="consent-section">
            <h4 className="consent-heading">
              <Lock size={15} style={{ verticalAlign: "middle", marginRight: "4px" }} />
              What Information Will Be Stored?
            </h4>
            <ul className="consent-list">
              <li>
                <strong>Original Form Text:</strong> The full clinical text or medical form you submit for extraction.
              </li>
              <li>
                <strong>Extracted Entities:</strong> Identified medications, clinical conditions, dates, and character offsets.
              </li>
              <li>
                <strong>Timestamps:</strong> The exact date and time the extraction record was created.
              </li>
            </ul>
          </div>

          <div className="consent-section">
            <h4 className="consent-heading">Why Is This Data Stored?</h4>
            <p className="consent-text">
              Saving your extraction history allows you to log in at any time to review past medical notes, examine highlighted entities, and track health information without re-running models.
            </p>
          </div>

          <div className="consent-section">
            <h4 className="consent-heading">Your Data Rights & Deletion</h4>
            <p className="consent-text">
              Extraction records are bound strictly to your authenticated account. You can permanently delete individual records or your entire extraction history at any time.
            </p>
          </div>

          <div className="consent-warning-box">
            <AlertTriangle size={18} style={{ color: "#d97706", flexShrink: 0, marginTop: "2px" }} />
            <div className="warning-text">
              <strong>Non-HIPAA Compliance Notice:</strong> This software is a clinical decision-support and educational prototype. It is <em>not certified for HIPAA compliance</em>. Please do not submit real, unencrypted Protected Health Information (PHI).
            </div>
          </div>
        </div>

        <div className="modal-actions" style={{ padding: "1.25rem 1.5rem", display: "flex", justifyContent: "flex-end", gap: "0.75rem", borderTop: "1px solid var(--border-subtle)" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel / Keep Private
          </button>
          <button
            ref={confirmBtnRef}
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
          >
            <Check size={16} />
            <span>I Consent & Save to History</span>
          </button>
        </div>
      </div>
    </div>
  );
}
