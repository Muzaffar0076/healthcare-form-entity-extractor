import React, { useState } from "react";
import {
  User,
  Shield,
  CheckCircle2,
  Info,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

/**
 * SettingsView: Simplified user-facing preferences page.
 * Focuses strictly on the user's profile and document storage consent.
 * Technical database and cryptographic details have been removed.
 */
export default function SettingsView({ onOpenConsent = () => {} }) {
  const { user, isAuthenticated } = useAuth();

  const getConsentKey = () =>
    user?._id ? `extraction_consent_${user._id}` : "extraction_consent_default";

  const [hasConsent, setHasConsent] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(getConsentKey()) === "granted";
  });

  const [feedback, setFeedback] = useState(null);

  const toggleConsent = () => {
    if (typeof window === "undefined") return;
    if (hasConsent) {
      localStorage.removeItem(getConsentKey());
      setHasConsent(false);
      setFeedback("Permission revoked. You will be asked before saving any new documents.");
    } else {
      localStorage.setItem(getConsentKey(), "granted");
      setHasConsent(true);
      setFeedback("Permission granted. You can now save extracted documents to your account.");
    }
    setTimeout(() => setFeedback(null), 3500);
  };

  return (
    <div className="settings-page-root">
      {/* Page Title */}
      <div className="settings-header">
        <h1 className="settings-title">Account & Preferences</h1>
        <p className="settings-subtitle">
          Manage your account profile and document privacy settings.
        </p>
      </div>

      {feedback && (
        <div className="settings-feedback-banner" role="status">
          <CheckCircle2 size={16} />
          <span>{feedback}</span>
        </div>
      )}

      <div className="settings-sections-grid">
        {/* Profile Details Card */}
        <section className="settings-card">
          <div className="settings-card-header">
            <div className="settings-icon-box">
              <User size={18} />
            </div>
            <div>
              <h2 className="settings-card-title">Account Profile</h2>
              <p className="settings-card-desc">
                Your personal account details.
              </p>
            </div>
          </div>

          <div className="settings-card-body">
            {isAuthenticated ? (
              <div className="settings-fields-list">
                <div className="settings-field-row">
                  <span className="field-label">Name</span>
                  <span className="field-value font-medium">{user?.fullName || "Not specified"}</span>
                </div>
                <div className="settings-field-row">
                  <span className="field-label">Email Address</span>
                  <span className="field-value">{user?.email}</span>
                </div>
                <div className="settings-field-row">
                  <span className="field-label">Account Role</span>
                  <span className="field-value">
                    <span className="settings-role-badge">{user?.role || "USER"}</span>
                  </span>
                </div>
              </div>
            ) : (
              <div className="settings-guest-notice">
                <p>You are using an anonymous guest session. Sign in to link your documents to an account.</p>
              </div>
            )}
          </div>
        </section>

        {/* Document Privacy & Saving Consent Card */}
        <section className="settings-card">
          <div className="settings-card-header">
            <div className="settings-icon-box">
              <Shield size={18} />
            </div>
            <div>
              <h2 className="settings-card-title">Document Storage Permission</h2>
              <p className="settings-card-desc">
                Control whether documents and findings can be saved to your account.
              </p>
            </div>
          </div>

          <div className="settings-card-body">
            <p className="settings-info-text">
              To respect your privacy, saving your documents requires your permission. You can enable or disable this at any time.
            </p>

            <div className="consent-toggle-row">
              <div className="consent-status-wrap">
                <span className="consent-status-label">Saving Documents:</span>
                <span
                  className={`status-pill ${
                    hasConsent ? "status-pill-success" : "status-pill-warning"
                  }`}
                >
                  {hasConsent ? "Allowed" : "Not Allowed"}
                </span>
              </div>

              <div className="consent-actions">
                <button
                  type="button"
                  className={`btn ${hasConsent ? "btn-outline-danger" : "btn-primary-sm"}`}
                  onClick={toggleConsent}
                >
                  {hasConsent ? "Disallow Saving" : "Allow Saving"}
                </button>
                <button
                  type="button"
                  className="btn btn-outline-sm"
                  onClick={onOpenConsent}
                >
                  View Privacy Terms
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* About Application Card */}
        <section className="settings-card" style={{ gridColumn: "1 / -1" }}>
          <div className="settings-card-header">
            <div className="settings-icon-box">
              <Info size={18} />
            </div>
            <div>
              <h2 className="settings-card-title">About This Tool</h2>
              <p className="settings-card-desc">
                General information about this healthcare document assistant.
              </p>
            </div>
          </div>

          <div className="settings-card-body">
            <div className="settings-fields-list">
              <div className="settings-field-row">
                <span className="field-label">Purpose</span>
                <span className="field-value">Educational healthcare document information finder</span>
              </div>
              <div className="settings-field-row">
                <span className="field-label">Information Detected</span>
                <span className="field-value">Medications, Dates, Medical Conditions</span>
              </div>
              <div className="settings-field-row">
                <span className="field-label">Medical Notice</span>
                <span className="field-value text-muted">For informational support only; does not provide medical diagnoses or advice.</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
