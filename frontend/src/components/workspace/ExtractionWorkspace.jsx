import React, { useState, useEffect } from "react";
import {
  FileText,
  FileUp,
  Sparkles,
  Trash2,
  AlertCircle,
  Bookmark,
  CheckCircle2,
  FileSearch,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import HighlightedText from "../HighlightedText";
import EntityInspector from "../EntityInspector";
import PDFUploader from "../PDFUploader";

const SAMPLES = [
  {
    title: "Prescription Note",
    text: "Patient was prescribed Aspirin on 12 March 2026 for diabetes.",
  },
  {
    title: "Doctor's Visit Note",
    text: "The 45-year-old female presented with acute pancreatitis and was started on Metformin on 04 October 2024.",
  },
  {
    title: "Discharge Summary",
    text: "Discharged on 15 January 2025 with resolution of bacterial pneumonia following treatment with Amoxicillin.",
  },
];

/**
 * ExtractionWorkspace: Focused, distraction-free document extraction workbench.
 * Left Pane: Document input (text or PDF) and highlighted reading view.
 * Right Pane: Categorized findings (Medications, Dates, Conditions) with copy tools.
 */
export default function ExtractionWorkspace({
  inputText,
  setInputText,
  inputMode,
  setInputMode,
  isLoading,
  setIsLoading,
  result,
  setResult,
  error,
  setError,
  selectedEntityIndex,
  setSelectedEntityIndex,
  onExtract,
  onClear,
  onPDFSuccess,
  onSaveToHistory,
  isSavingHistory,
  savedRecordId,
  saveSuccessMessage,
  setAnnouncement,
  setToastMessage,
}) {
  const { isAuthenticated } = useAuth();
  const [docViewMode, setDocViewMode] = useState("highlights");

  // Reset docViewMode to highlights whenever new extraction results arrive
  useEffect(() => {
    if (result) {
      setDocViewMode("highlights");
    }
  }, [result]);

  // Support Cmd+Enter / Ctrl+Enter shortcut for extraction
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        if (inputMode === "text" && !isLoading && inputText.trim()) {
          e.preventDefault();
          onExtract();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [inputMode, isLoading, inputText, onExtract]);

  const handleSelectSample = (sample) => {
    setInputText(sample.text);
    setError(null);
    setAnnouncement(`Loaded sample: ${sample.title}`);
  };

  return (
    <div className="extraction-workspace-root">
      {/* Workspace Top Toolbar */}
      <div className="workspace-toolbar">
        <div className="workspace-toolbar-left">
          {/* Mode Switcher */}
          <div className="segmented-control" role="tablist" aria-label="Input Mode Switcher">
            <button
              type="button"
              role="tab"
              aria-selected={inputMode === "text"}
              className={`segmented-tab ${inputMode === "text" ? "active" : ""}`}
              onClick={() => {
                setInputMode("text");
                setError(null);
              }}
            >
              <FileText size={15} />
              <span>Type or Paste Text</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={inputMode === "pdf"}
              className={`segmented-tab ${inputMode === "pdf" ? "active" : ""}`}
              onClick={() => {
                setInputMode("pdf");
                setError(null);
              }}
            >
              <FileUp size={15} />
              <span>Upload PDF Document</span>
            </button>
          </div>
        </div>

        {/* Quick Sample Selector */}
        {inputMode === "text" && (
          <div className="workspace-toolbar-right">
            <span className="sample-hint-label">Try an example:</span>
            <div className="sample-pills-row">
              {SAMPLES.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="sample-pill-btn"
                  onClick={() => handleSelectSample(s)}
                >
                  {s.title}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Split-Pane Workspace */}
      <div className="workspace-split-container">
        {/* Left Pane: Document Ingestion & Reading View */}
        <section className="workspace-pane pane-document" aria-label="Document Input and Highlights">
          <div className="pane-header-bar">
            <div className="pane-header-title-group">
              <span className="pane-title">
                {result && docViewMode === "highlights"
                  ? "Document with Highlights"
                  : inputMode === "pdf"
                  ? "Upload Healthcare PDF"
                  : "Healthcare Document Text"}
              </span>
              {result && (
                <span className="pane-badge">
                  {result.entities ? result.entities.length : 0} Details Found
                </span>
              )}
            </div>

            {/* Toggle between Highlights and Raw Text when results exist */}
            {result && inputMode === "text" && (
              <div className="doc-view-switcher">
                <button
                  type="button"
                  className={`doc-view-btn ${docViewMode === "highlights" ? "active" : ""}`}
                  onClick={() => setDocViewMode("highlights")}
                >
                  Highlights
                </button>
                <button
                  type="button"
                  className={`doc-view-btn ${docViewMode === "editor" ? "active" : ""}`}
                  onClick={() => setDocViewMode("editor")}
                >
                  Original Text
                </button>
              </div>
            )}
          </div>

          <div className="pane-content-body">
            {/* Direct Text Mode */}
            {inputMode === "text" ? (
              result && docViewMode === "highlights" ? (
                /* Interactive Reading View */
                <div className="highlight-scroll-wrapper">
                  <HighlightedText
                    text={result.text}
                    entities={result.entities || []}
                    selectedEntityIndex={selectedEntityIndex}
                    onSelectEntity={(idx) => setSelectedEntityIndex(idx)}
                    className="saas-highlighted-text"
                    idPrefix="saas-ent-"
                  />
                  <div className="highlight-footer-note">
                    <span>Click any highlighted word to view it in the right pane.</span>
                    <button
                      type="button"
                      className="link-btn-text"
                      onClick={() => setDocViewMode("editor")}
                    >
                      Edit Original Text
                    </button>
                  </div>
                </div>
              ) : (
                /* Textarea Editor */
                <div className="textarea-editor-wrapper">
                  <label htmlFor="saas-clinical-textarea" className="visually-hidden">
                    Healthcare Document Text
                  </label>
                  <textarea
                    id="saas-clinical-textarea"
                    className="saas-textarea"
                    placeholder="Paste your doctor's notes, medical prescription, or discharge summary here..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    rows={12}
                  />

                  <div className="textarea-footer-bar">
                    <span className="char-count-info">
                      {inputText.length} characters
                    </span>
                    <div className="editor-actions">
                      {inputText.length > 0 && (
                        <button
                          type="button"
                          className="btn btn-secondary-sm"
                          onClick={onClear}
                          disabled={isLoading}
                        >
                          <Trash2 size={14} />
                          <span>Clear</span>
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-primary-sm btn-extract"
                        onClick={onExtract}
                        disabled={isLoading || !inputText.trim()}
                        title="Extract information (Cmd + Enter)"
                      >
                        {isLoading ? (
                          <>
                            <RefreshCw size={14} className="spin-icon" />
                            <span>Processing Document...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles size={14} />
                            <span>Extract Information</span>
                            <span className="kbd-shortcut">⌘↵</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )
            ) : (
              /* PDF Upload Mode */
              <div className="pdf-upload-pane-wrap">
                <PDFUploader
                  onExtractionSuccess={onPDFSuccess}
                  isLoading={isLoading}
                  setIsLoading={setIsLoading}
                />
                {result && result.text && (
                  <div className="pdf-extracted-text-section">
                    <div className="pane-header-bar" style={{ marginTop: "1rem" }}>
                      <span className="pane-title">Extracted Document Text</span>
                    </div>
                    <div className="highlight-scroll-wrapper">
                      <HighlightedText
                        text={result.text}
                        entities={result.entities || []}
                        selectedEntityIndex={selectedEntityIndex}
                        onSelectEntity={(idx) => setSelectedEntityIndex(idx)}
                        className="saas-highlighted-text"
                        idPrefix="pdf-saas-ent-"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="saas-error-banner" role="alert">
                <AlertCircle size={16} />
                <span className="error-text">{error}</span>
                <button
                  type="button"
                  className="error-dismiss-btn"
                  onClick={() => setError(null)}
                  aria-label="Dismiss error"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Right Pane: Detected Healthcare Details */}
        <section className="workspace-pane pane-inspector" aria-label="Detected Medical Details">
          <div className="pane-header-bar">
            <div className="pane-header-title-group">
              <span className="pane-title">Detected Details</span>
              {result?.metadata && (
                <span className="pane-meta-pill">
                  {result.metadata.fileName}
                </span>
              )}
            </div>

            {/* Save to History Button for Logged-In Users */}
            {result && isAuthenticated && (
              <div className="pane-header-actions">
                {savedRecordId ? (
                  <span className="saved-badge">
                    <CheckCircle2 size={13} />
                    <span>Saved</span>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="btn btn-outline-sm btn-save-record"
                    onClick={onSaveToHistory}
                    disabled={isSavingHistory}
                    title="Save this document to your private history"
                  >
                    <Bookmark size={13} />
                    <span>{isSavingHistory ? "Saving..." : "Save Document"}</span>
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="pane-content-body">
            {!result ? (
              /* Awaiting Extraction Friendly State */
              <div className="workspace-empty-state">
                <div className="empty-state-icon-box">
                  <FileSearch size={32} />
                </div>
                <h3 className="empty-state-title">Ready to Extract</h3>
                <p className="empty-state-description">
                  Upload a medical PDF or paste clinical text on the left, then click <strong>Extract Information</strong> to locate medications, dates, and medical conditions.
                </p>

                <div className="entity-legend-preview">
                  <span className="legend-tag tag-med">Medications</span>
                  <span className="legend-tag tag-date">Dates</span>
                  <span className="legend-tag tag-cond">Conditions</span>
                </div>
              </div>
            ) : result.entities && result.entities.length > 0 ? (
              /* Populated Details */
              <EntityInspector
                entities={result.entities}
                selectedEntityIndex={selectedEntityIndex}
                onSelectEntity={(idx) => setSelectedEntityIndex(idx)}
                onCopyFeedback={(msg) => {
                  setAnnouncement(msg);
                  setToastMessage(msg);
                  setTimeout(() => setToastMessage(null), 2500);
                }}
              />
            ) : (
              /* Zero Details Found */
              <div className="workspace-empty-state">
                <div className="empty-state-icon-box">
                  <CheckCircle2 size={32} style={{ color: "var(--text-muted)" }} />
                </div>
                <h3 className="empty-state-title">No Medical Details Found</h3>
                <p className="empty-state-description">
                  No recognized medications, dates, or medical conditions were found in this document. Try checking the text or uploading a different document.
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
