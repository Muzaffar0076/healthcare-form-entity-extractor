import React, { useState, useEffect, useRef } from "react";
import { X, Calendar, FileText, Trash2, Copy, Check } from "lucide-react";
import HighlightedText from "./HighlightedText";
import { formatDate } from "../utils/formatters";

/**
 * HistoryDetailModal: Displays a previously saved healthcare document
 * with highlights and detected information. Developer ID hashes removed.
 */
export default function HistoryDetailModal({
  isOpen,
  record,
  onClose,
  onDelete,
}) {
  const [selectedEntityIndex, setSelectedEntityIndex] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const modalRef = useRef(null);

  // Handle ESC key to dismiss modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      setSelectedEntityIndex(null);
      setCopiedId(null);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !record) return null;

  const { id, form_text, extracted_entities, created_at, entity_counts } = record;
  const entities = extracted_entities?.entities || [];
  const formattedDate = formatDate(created_at);

  const handleCopyText = async (textToCopy, copyKey) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedId(copyKey);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Clipboard write failed
    }
  };

  const getFriendlyLabel = (label) => {
    switch (label) {
      case "MEDICATION":
        return "Medication";
      case "DATE":
        return "Date";
      case "CONDITION":
        return "Condition";
      default:
        return label;
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={modalRef}
        className="modal-card history-detail-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge badge-primary">
              <FileText size={20} />
            </div>
            <div>
              <h2 id="detail-title">Saved Document Details</h2>
              <div className="detail-meta-line">
                <span className="detail-date">
                  <Calendar size={13} style={{ verticalAlign: "middle", marginRight: "4px" }} />
                  {formattedDate}
                </span>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close document details"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Information Type Summary */}
          <div className="legend" style={{ margin: "0.25rem 0 1rem 0" }}>
            <span className="legend-chip chip-medication">
              Medications ({entity_counts?.MEDICATION || 0})
            </span>
            <span className="legend-chip chip-date">
              Dates ({entity_counts?.DATE || 0})
            </span>
            <span className="legend-chip chip-condition">
              Conditions ({entity_counts?.CONDITION || 0})
            </span>
          </div>

          {/* Highlighted Document Text */}
          <div className="detail-section">
            <div className="detail-section-title">
              <span>Document with Highlights</span>
              <span className="char-counter">{form_text?.length || 0} characters</span>
            </div>
            <HighlightedText
              text={form_text}
              entities={entities}
              selectedEntityIndex={selectedEntityIndex}
              onSelectEntity={(idx) => setSelectedEntityIndex(idx)}
              className="highlight-display detail-highlight-scroll"
              idPrefix="modal-ent-"
            />
          </div>

          {/* Extracted Details List */}
          <div className="detail-section" style={{ marginTop: "1.25rem" }}>
            <div className="detail-section-title">
              <span>Detected Details ({entities.length})</span>
              <span className="sample-label">Click an item to highlight in text</span>
            </div>

            {entities.length === 0 ? (
              <p className="detail-empty-note">No medical details found in this document.</p>
            ) : (
              <div className="modal-entities-grid">
                {entities.map((ent, idx) => {
                  const isSelected = selectedEntityIndex === idx;
                  const isCopied = copiedId === idx;

                  return (
                    <div
                      key={`modal-ent-${idx}`}
                      className={`modal-entity-card ${isSelected ? "selected" : ""}`}
                      onClick={() => setSelectedEntityIndex(idx)}
                      role="button"
                      tabIndex={0}
                      title="Click to locate in text above"
                    >
                      <div className="modal-entity-card-row">
                        <span className="modal-entity-text">{ent.text}</span>
                        <span className={`entity-tag tag-${ent.label}`}>
                          {getFriendlyLabel(ent.label)}
                        </span>
                      </div>
                      <div className="modal-entity-actions-row">
                        <button
                          type="button"
                          className="btn-modal-copy"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopyText(ent.text, idx);
                          }}
                          title={`Copy "${ent.text}"`}
                        >
                          {isCopied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                          <span>{isCopied ? "Copied" : "Copy"}</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="modal-actions" style={{ justifyContent: "space-between" }}>
          <button
            type="button"
            className="btn btn-outline-danger"
            onClick={() => onDelete(id)}
            title="Delete this saved document"
          >
            <Trash2 size={14} />
            <span>Delete Document</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
