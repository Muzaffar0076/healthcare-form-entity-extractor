import React, { useState, useEffect } from "react";
import { Activity, Sparkles, Trash2, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";

const API_BASE = "http://localhost:8000";

const SAMPLES = [
  {
    title: "Prescription & Date",
    text: "Patient was prescribed Aspirin on 12 March 2026 for diabetes.",
  },
  {
    title: "Clinical Condition",
    text: "The 45-year-old female presented with acute pancreatitis and was started on Metformin on 04 October 2024.",
  },
  {
    title: "Discharge Summary",
    text: "Discharged on 15 January 2025 with resolution of bacterial pneumonia following treatment with Amoxicillin.",
  },
];

export default function App() {
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [apiOnline, setApiOnline] = useState(null);

  // Check backend health on mount
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => setApiOnline(data.status === "healthy"))
      .catch(() => setApiOnline(false));
  }, []);

  const handleExtract = async () => {
    const trimmed = inputText.trim();
    if (!trimmed) {
      setError("Please enter or paste healthcare form text before extracting.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/v1/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || `Server error (${response.status})`);
      }

      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to connect to extraction backend.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setInputText("");
    setResult(null);
    setError(null);
  };

  // Render original text with embedded entity highlight badges
  const renderHighlightedText = () => {
    if (!result || !result.text) return null;

    const { text, entities } = result;
    if (!entities || entities.length === 0) {
      return <span>{text}</span>;
    }

    // Sort entities by start offset
    const sorted = [...entities].sort((a, b) => a.start - b.start);
    const elements = [];
    let lastIndex = 0;

    sorted.forEach((ent, idx) => {
      // Append non-entity text preceding this entity
      if (ent.start > lastIndex) {
        elements.push(
          <span key={`text-${lastIndex}`}>{text.slice(lastIndex, ent.start)}</span>
        );
      }

      // Append highlighted entity
      elements.push(
        <mark
          key={`entity-${idx}-${ent.start}`}
          className={`entity-span entity-${ent.label}`}
        >
          {text.slice(ent.start, ent.end)}
          <span className={`entity-tag tag-${ent.label}`}>{ent.label}</span>
        </mark>
      );

      lastIndex = ent.end;
    });

    // Append any trailing text
    if (lastIndex < text.length) {
      elements.push(<span key={`text-tail`}>{text.slice(lastIndex)}</span>);
    }

    return elements;
  };

  return (
    <div className="container">
      {/* Header */}
      <header className="app-header">
        <div className="title-group">
          <h1>Healthcare Form Entity Extractor</h1>
          <p>Assisting patients and care navigators in locating critical healthcare details.</p>
        </div>

        <div className="status-badge" title="FastAPI Backend Status">
          <span
            className={`status-dot ${
              apiOnline === true
                ? "status-online"
                : apiOnline === false
                ? "status-offline"
                : ""
            }`}
          />
          <span>
            {apiOnline === true
              ? "Backend Online (BiLSTM-CRF)"
              : apiOnline === false
              ? "Backend Offline"
              : "Checking API..."}
          </span>
        </div>
      </header>

      {/* Entity Legend */}
      <div className="legend">
        <span className="legend-chip chip-medication">MEDICATION (Medicines & Drugs)</span>
        <span className="legend-chip chip-date">DATE (Dates & Timestamps)</span>
        <span className="legend-chip chip-condition">CONDITION (Diseases & Symptoms)</span>
      </div>

      {/* Main Input Card */}
      <section className="card">
        <div className="card-title">
          <span>Input Healthcare Form Text</span>
          <span className="char-counter">{inputText.length} characters</span>
        </div>

        {/* Sample text buttons */}
        <div className="sample-bar">
          <span className="sample-label">Try an example:</span>
          {SAMPLES.map((s, i) => (
            <button
              key={i}
              type="button"
              className="sample-btn"
              onClick={() => {
                setInputText(s.text);
                setError(null);
              }}
            >
              {s.title}
            </button>
          ))}
        </div>

        <textarea
          className="input-textarea"
          placeholder="Paste medical instructions, intake form text, or clinical discharge notes here..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />

        <div className="button-bar">
          <div className="action-btn-group">
            <button
              type="button"
              className="btn btn-primary"
              disabled={isLoading}
              onClick={handleExtract}
            >
              <Sparkles size={16} />
              {isLoading ? "Extracting..." : "Extract Entities"}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClear}
            >
              <Trash2 size={16} />
              Clear
            </button>
          </div>
        </div>

        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
      </section>

      {/* Results Section */}
      {result && (
        <section className="card">
          <div className="card-title">
            <span>Extraction Preview</span>
            <span className="legend-chip" style={{ background: "#f1f5f9", color: "#475569" }}>
              Model: {result.modelVersion}
            </span>
          </div>

          {result.entities.length > 0 ? (
            <>
              {/* In-Text Highlighting View */}
              <div className="highlight-display">
                {renderHighlightedText()}
              </div>

              {/* Structured Extracted List */}
              <div className="entity-grid">
                {result.entities.map((ent, idx) => (
                  <div key={idx} className="entity-card">
                    <div className="entity-card-header">
                      <span className="entity-card-text">{ent.text}</span>
                      <span className={`entity-tag tag-${ent.label}`}>
                        {ent.label}
                      </span>
                    </div>
                    <div className="entity-card-meta">
                      <span>Positions: {ent.start}–{ent.end}</span>
                      {ent.confidence !== null && (
                        <span>Confidence: {Math.round(ent.confidence * 100)}%</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-box">
              <CheckCircle2 size={32} style={{ color: "#94a3b8", marginBottom: "0.5rem" }} />
              <p>No healthcare entities (Medication, Date, Condition) detected in this text.</p>
            </div>
          )}
        </section>
      )}

      {/* Disclaimer */}
      <footer className="app-footer">
        <p style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem" }}>
          <ShieldAlert size={16} />
          <strong>Medical Information Extraction Prototype:</strong> This tool is an educational decision-support aid and does not constitute medical advice or clinical diagnosis.
        </p>
      </footer>
    </div>
  );
}
