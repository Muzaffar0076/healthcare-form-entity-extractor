import React from "react";
import {
  HelpCircle,
  Pill,
  Calendar,
  Activity,
  ShieldAlert,
  Keyboard,
  Workflow,
  Sparkles,
} from "lucide-react";

/**
 * HelpView: Clean, everyday guide for patients and care navigators.
 * Explains supported medical details, simple 4-step workflow, and safety disclaimer.
 * Internal model architecture and ML jargon have been removed.
 */
export default function HelpView() {
  const entityCategories = [
    {
      label: "MEDICATION",
      icon: Pill,
      colorClass: "theme-emerald",
      badgeClass: "tag-med",
      title: "Medications & Prescriptions",
      description:
        "Prescription medicines, over-the-counter drugs, and dosages found in your notes.",
      examples: ["Metformin 500mg", "Aspirin", "Amoxicillin", "Lisinopril 10mg"],
    },
    {
      label: "DATE",
      icon: Calendar,
      colorClass: "theme-blue",
      badgeClass: "tag-date",
      title: "Dates & Timelines",
      description:
        "Calendar dates for doctor appointments, prescription dates, or hospital visits.",
      examples: ["12 March 2026", "04 October 2024", "15 January 2025"],
    },
    {
      label: "CONDITION",
      icon: Activity,
      colorClass: "theme-rose",
      badgeClass: "tag-cond",
      title: "Medical Conditions & Symptoms",
      description:
        "Diagnoses, health conditions, symptoms, and illness names in your documents.",
      examples: ["diabetes", "acute pancreatitis", "bacterial pneumonia", "hypertension"],
    },
  ];

  const shortcuts = [
    { key: "⌘ + Enter / Ctrl + Enter", description: "Extract information from your text" },
    { key: "Esc", description: "Close any open dialog or menu" },
    { key: "Tab / Shift + Tab", description: "Move between buttons and inputs" },
    { key: "Enter / Space", description: "Select a highlighted item" },
  ];

  return (
    <div className="help-page-root">
      {/* Page Header */}
      <div className="help-header">
        <h1 className="help-title">Help & Guide</h1>
        <p className="help-subtitle">
          Learn how to use this tool and understand what healthcare information it can find.
        </p>
      </div>

      {/* Prominent Safety Notice */}
      <div className="help-disclaimer-banner" role="alert">
        <div className="disclaimer-icon-wrap">
          <ShieldAlert size={22} />
        </div>
        <div className="disclaimer-content">
          <h2 className="disclaimer-title">Important Medical Notice</h2>
          <p className="disclaimer-text">
            This application is an educational assistant designed to help you read and organize healthcare documents. <strong>It does not provide medical diagnoses, treatment recommendations, or medical advice.</strong> Always consult your doctor or healthcare provider for clinical decisions.
          </p>
        </div>
      </div>

      {/* Supported Categories */}
      <section className="help-section">
        <div className="help-section-header">
          <Sparkles size={18} className="text-primary" />
          <h2 className="help-section-title">What Information We Can Find</h2>
        </div>
        <p className="help-section-subtitle">
          This tool automatically searches for three essential types of information in your documents:
        </p>

        <div className="entity-guide-grid">
          {entityCategories.map((cat) => {
            const Icon = cat.icon;
            return (
              <div key={cat.label} className={`entity-guide-card ${cat.colorClass}`}>
                <div className="guide-card-top">
                  <span className={`entity-tag ${cat.badgeClass}`}>{cat.label}</span>
                  <div className="guide-icon-wrap">
                    <Icon size={18} />
                  </div>
                </div>

                <h3 className="guide-card-title">{cat.title}</h3>
                <p className="guide-card-desc">{cat.description}</p>

                <div className="guide-examples-wrap">
                  <span className="examples-label">Examples:</span>
                  <div className="examples-tags-row">
                    {cat.examples.map((ex, i) => (
                      <span key={i} className="example-tag">
                        {ex}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Step-by-Step Workflow */}
      <section className="help-section">
        <div className="help-section-header">
          <Workflow size={18} className="text-primary" />
          <h2 className="help-section-title">How It Works in 4 Steps</h2>
        </div>

        <div className="workflow-steps-list">
          <div className="workflow-step-item">
            <div className="step-number-circle">1</div>
            <div className="step-info">
              <h3 className="step-title">Add Your Document</h3>
              <p className="step-desc">
                Paste doctor instructions or medical notes directly, or upload a medical PDF file.
              </p>
            </div>
          </div>

          <div className="workflow-step-item">
            <div className="step-number-circle">2</div>
            <div className="step-info">
              <h3 className="step-title">Extract Key Details</h3>
              <p className="step-desc">
                Click <strong>Extract Information</strong>. The tool reads the text and identifies all medicines, dates, and conditions.
              </p>
            </div>
          </div>

          <div className="workflow-step-item">
            <div className="step-number-circle">3</div>
            <div className="step-info">
              <h3 className="step-title">Review the Highlights</h3>
              <p className="step-desc">
                Click any highlighted item in your text to see its details, or click an item on the right to see where it appears in your document.
              </p>
            </div>
          </div>

          <div className="workflow-step-item">
            <div className="step-number-circle">4</div>
            <div className="step-info">
              <h3 className="step-title">Save or Copy</h3>
              <p className="step-desc">
                Copy individual items or the full list to your clipboard. If signed in, you can save the document to your private history.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Keyboard Shortcuts */}
      <section className="help-section">
        <div className="help-section-header">
          <Keyboard size={18} className="text-primary" />
          <h2 className="help-section-title">Keyboard Shortcuts</h2>
        </div>

        <div className="shortcuts-table-wrap">
          <table className="shortcuts-table">
            <thead>
              <tr>
                <th>Shortcut</th>
                <th>What It Does</th>
              </tr>
            </thead>
            <tbody>
              {shortcuts.map((sc, i) => (
                <tr key={i}>
                  <td>
                    <kbd className="kbd-badge">{sc.key}</kbd>
                  </td>
                  <td>{sc.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
