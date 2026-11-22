import React, { useState } from "react";
import {
  Copy,
  Check,
  Pill,
  Calendar,
  Activity,
  Layers,
} from "lucide-react";
import { getConfidenceInfo } from "../utils/formatters";

/**
 * EntityInspector: Displays structured, categorized healthcare details
 * (Medications, Dates, Medical Conditions) with filtering, one-click copy,
 * and bi-directional highlight synchronization.
 * Stripped of all developer offsets and technical jargon.
 */
export default function EntityInspector({
  entities = [],
  selectedEntityIndex = null,
  onSelectEntity = () => {},
  onCopyFeedback = () => {},
}) {
  const [filterType, setFilterType] = useState("ALL"); // "ALL" | "MEDICATION" | "CONDITION" | "DATE"
  const [copiedId, setCopiedId] = useState(null);

  // Group count calculation
  const counts = entities.reduce((acc, ent) => {
    acc[ent.label] = (acc[ent.label] || 0) + 1;
    return acc;
  }, {});

  const filteredEntities = entities.filter((ent) => {
    if (filterType === "ALL") return true;
    return ent.label === filterType;
  });

  const handleCopySingle = async (e, ent, originalIdx) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(ent.text);
      setCopiedId(originalIdx);
      onCopyFeedback(`Copied "${ent.text}"`);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      onCopyFeedback("Failed to copy to clipboard");
    }
  };

  const handleCopyAll = async () => {
    if (!entities || entities.length === 0) return;

    const meds = entities.filter((e) => e.label === "MEDICATION").map((e) => e.text);
    const conds = entities.filter((e) => e.label === "CONDITION").map((e) => e.text);
    const dates = entities.filter((e) => e.label === "DATE").map((e) => e.text);

    let summaryText = "Healthcare Document Key Details\n";
    summaryText += "================================\n\n";

    if (meds.length > 0) {
      summaryText += `MEDICATIONS (${meds.length}):\n`;
      meds.forEach((m) => (summaryText += ` • ${m}\n`));
      summaryText += "\n";
    }

    if (conds.length > 0) {
      summaryText += `MEDICAL CONDITIONS (${conds.length}):\n`;
      conds.forEach((c) => (summaryText += ` • ${c}\n`));
      summaryText += "\n";
    }

    if (dates.length > 0) {
      summaryText += `DATES (${dates.length}):\n`;
      dates.forEach((d) => (summaryText += ` • ${d}\n`));
      summaryText += "\n";
    }

    try {
      await navigator.clipboard.writeText(summaryText);
      setCopiedId("ALL");
      onCopyFeedback("Copied all details to clipboard");
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      onCopyFeedback("Failed to copy summary");
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
    <div className="entity-inspector-container">
      {/* Category Filter & Action Bar */}
      <div className="inspector-controls-bar">
        <div className="filter-pill-group" role="tablist" aria-label="Information Filters">
          <button
            type="button"
            role="tab"
            aria-selected={filterType === "ALL"}
            className={`filter-tab ${filterType === "ALL" ? "active" : ""}`}
            onClick={() => setFilterType("ALL")}
          >
            <Layers size={13} />
            <span>All ({entities.length})</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={filterType === "MEDICATION"}
            className={`filter-tab filter-med ${filterType === "MEDICATION" ? "active" : ""}`}
            onClick={() => setFilterType("MEDICATION")}
          >
            <span>Medications ({counts.MEDICATION || 0})</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={filterType === "CONDITION"}
            className={`filter-tab filter-cond ${filterType === "CONDITION" ? "active" : ""}`}
            onClick={() => setFilterType("CONDITION")}
          >
            <span>Conditions ({counts.CONDITION || 0})</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={filterType === "DATE"}
            className={`filter-tab filter-date ${filterType === "DATE" ? "active" : ""}`}
            onClick={() => setFilterType("DATE")}
          >
            <span>Dates ({counts.DATE || 0})</span>
          </button>
        </div>

        <div className="inspector-utility-actions">
          <button
            type="button"
            className="btn btn-outline-sm btn-copy-all"
            onClick={handleCopyAll}
            title="Copy all detected items to your clipboard"
          >
            {copiedId === "ALL" ? <Check size={14} className="text-success" /> : <Copy size={14} />}
            <span>{copiedId === "ALL" ? "Copied!" : "Copy All Details"}</span>
          </button>
        </div>
      </div>

      {/* Structured Details Cards */}
      <div className="entity-cards-scroll-container">
        {filteredEntities.length === 0 ? (
          <div className="empty-filter-state">
            <p>No items found under this filter.</p>
          </div>
        ) : (
          <div className="entity-cards-grid">
            {filteredEntities.map((ent) => {
              const originalIndex = entities.findIndex(
                (orig) => orig.start === ent.start && orig.end === ent.end && orig.label === ent.label
              );
              const isSelected = selectedEntityIndex === originalIndex;
              const confidence = getConfidenceInfo(ent.confidence);
              const isCopied = copiedId === originalIndex;

              return (
                <div
                  key={`ent-card-${originalIndex}-${ent.start}`}
                  className={`entity-card interactive ${isSelected ? "selected" : ""}`}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  onClick={() => onSelectEntity(originalIndex, ent)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectEntity(originalIndex, ent);
                    }
                  }}
                  title="Click to highlight where this appears in your document"
                >
                  <div className="entity-card-header">
                    <span className="entity-card-text">{ent.text}</span>
                    <div className="entity-header-actions">
                      <span className={`entity-tag tag-${ent.label}`}>
                        {getFriendlyLabel(ent.label)}
                      </span>
                      <button
                        type="button"
                        className="btn-card-copy"
                        onClick={(e) => handleCopySingle(e, ent, originalIndex)}
                        title={`Copy "${ent.text}"`}
                        aria-label={`Copy ${ent.text}`}
                      >
                        {isCopied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                      </button>
                    </div>
                  </div>

                  <div className="entity-card-footer">
                    {confidence.label && (
                      <span className={`confidence-chip confidence-${confidence.level}`}>
                        {confidence.label}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
