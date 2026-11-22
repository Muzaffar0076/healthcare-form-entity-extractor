import React, { useState, useEffect, useRef } from "react";
import { AlertCircle, CheckCircle2, Lock, Mail, Phone, User, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function AuthModal({ isOpen, onClose, initialTab = "login" }) {
  const { login, register, authError, clearAuthError } = useAuth();

  const [activeTab, setActiveTab] = useState(initialTab); // "login" | "register"
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    phoneNumber: "",
  });

  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const emailInputRef = useRef(null);

  // Sync initial tab when opening and auto-focus email
  useEffect(() => {
    setActiveTab(initialTab);
    setFormErrors({});
    clearAuthError();
    setSuccessMessage(null);
    if (isOpen) {
      setTimeout(() => emailInputRef.current?.focus(), 60);
    }
  }, [initialTab, isOpen, clearAuthError]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (formErrors[field]) {
      setFormErrors((prev) => ({ ...prev, [field]: null }));
    }
    clearAuthError();
  };

  const validateForm = () => {
    const errors = {};

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.email.trim()) {
      errors.email = "Email address is required.";
    } else if (!emailRegex.test(formData.email.trim())) {
      errors.email = "Please enter a valid email address.";
    }

    // Password validation
    if (!formData.password) {
      errors.password = "Password is required.";
    } else if (formData.password.length < 8) {
      errors.password = "Password must be at least 8 characters long.";
    } else if (!/[A-Za-z]/.test(formData.password) || !/[0-9]/.test(formData.password)) {
      errors.password = "Password must contain at least one letter and one number.";
    }

    if (activeTab === "register") {
      // Full Name validation
      if (!formData.fullName.trim() || formData.fullName.trim().length < 2) {
        errors.fullName = "Full name must be at least 2 characters long.";
      }

      // Confirm Password validation
      if (formData.password !== formData.confirmPassword) {
        errors.confirmPassword = "Passwords do not match.";
      }

      // Phone validation (optional)
      if (formData.phoneNumber && formData.phoneNumber.trim()) {
        const phoneRegex = /^\+?[0-9\s\-()]{7,25}$/;
        if (!phoneRegex.test(formData.phoneNumber.trim())) {
          errors.phoneNumber = "Please enter a valid phone number (e.g. +1-555-0123).";
        }
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    setSuccessMessage(null);

    try {
      if (activeTab === "login") {
        await login(formData.email.trim(), formData.password);
        setSuccessMessage("Logged in successfully!");
        setTimeout(() => {
          onClose();
        }, 600);
      } else {
        await register({
          fullName: formData.fullName.trim(),
          email: formData.email.trim(),
          password: formData.password,
          confirmPassword: formData.confirmPassword,
          phoneNumber: formData.phoneNumber.trim() || null,
        });
        setSuccessMessage("Registration successful! Welcome.");
        setTimeout(() => {
          onClose();
        }, 700);
      }
    } catch (err) {
      // Error handled by AuthContext (authError)
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <div className="modal-header">
          <div className="modal-tabs">
            <button
              type="button"
              className={`modal-tab-btn ${activeTab === "login" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("login");
                setFormErrors({});
                clearAuthError();
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`modal-tab-btn ${activeTab === "register" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("register");
                setFormErrors({});
                clearAuthError();
              }}
            >
              Create Account
            </button>
          </div>

          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit} noValidate>
          <h2 id="auth-modal-title" className="modal-title">
            {activeTab === "login" ? "Sign In to Your Account" : "Register a New Account"}
          </h2>
          <p className="modal-subtitle">
            {activeTab === "login"
              ? "Access healthcare entity extraction with your verified account."
              : "Create an account to securely save and access healthcare form tools."}
          </p>

          {/* Success Banner */}
          {successMessage && (
            <div className="auth-alert alert-success">
              <CheckCircle2 size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Global Auth Error */}
          {authError && (
            <div className="auth-alert alert-error">
              <AlertCircle size={16} />
              <span>{authError}</span>
            </div>
          )}

          {/* Full Name (Register only) */}
          {activeTab === "register" && (
            <div className="form-group">
              <label htmlFor="reg-fullName">
                Full Name <span className="req-star">*</span>
              </label>
              <div className="input-with-icon">
                <User size={16} className="input-icon" />
                <input
                  id="reg-fullName"
                  type="text"
                  placeholder="e.g. Dr. Jane Doe"
                  value={formData.fullName}
                  onChange={(e) => handleInputChange("fullName", e.target.value)}
                  className={formErrors.fullName ? "input-error" : ""}
                />
              </div>
              {formErrors.fullName && (
                <span className="field-error-text">{formErrors.fullName}</span>
              )}
            </div>
          )}

          {/* Email Address */}
          <div className="form-group">
            <label htmlFor="auth-email">
              Email Address <span className="req-star">*</span>
            </label>
            <div className="input-with-icon">
              <Mail size={16} className="input-icon" />
              <input
                ref={emailInputRef}
                id="auth-email"
                type="email"
                placeholder="name@example.com"
                value={formData.email}
                onChange={(e) => handleInputChange("email", e.target.value)}
                className={formErrors.email ? "input-error" : ""}
                autoComplete="email"
              />
            </div>
            {formErrors.email && (
              <span className="field-error-text">{formErrors.email}</span>
            )}
          </div>

          {/* Phone Number (Register only, optional) */}
          {activeTab === "register" && (
            <div className="form-group">
              <label htmlFor="reg-phone">
                Phone Number <span className="opt-tag">(Optional)</span>
              </label>
              <div className="input-with-icon">
                <Phone size={16} className="input-icon" />
                <input
                  id="reg-phone"
                  type="tel"
                  placeholder="+1-555-0199"
                  value={formData.phoneNumber}
                  onChange={(e) => handleInputChange("phoneNumber", e.target.value)}
                  className={formErrors.phoneNumber ? "input-error" : ""}
                />
              </div>
              {formErrors.phoneNumber && (
                <span className="field-error-text">{formErrors.phoneNumber}</span>
              )}
            </div>
          )}

          {/* Password */}
          <div className="form-group">
            <label htmlFor="auth-password">
              Password <span className="req-star">*</span>
            </label>
            <div className="input-with-icon">
              <Lock size={16} className="input-icon" />
              <input
                id="auth-password"
                type="password"
                placeholder="Minimum 8 characters (letters & numbers)"
                value={formData.password}
                onChange={(e) => handleInputChange("password", e.target.value)}
                className={formErrors.password ? "input-error" : ""}
                autoComplete={activeTab === "login" ? "current-password" : "new-password"}
              />
            </div>
            {formErrors.password && (
              <span className="field-error-text">{formErrors.password}</span>
            )}
          </div>

          {/* Confirm Password (Register only) */}
          {activeTab === "register" && (
            <div className="form-group">
              <label htmlFor="reg-confirmPassword">
                Confirm Password <span className="req-star">*</span>
              </label>
              <div className="input-with-icon">
                <Lock size={16} className="input-icon" />
                <input
                  id="reg-confirmPassword"
                  type="password"
                  placeholder="Re-enter password"
                  value={formData.confirmPassword}
                  onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                  className={formErrors.confirmPassword ? "input-error" : ""}
                  autoComplete="new-password"
                />
              </div>
              {formErrors.confirmPassword && (
                <span className="field-error-text">{formErrors.confirmPassword}</span>
              )}
            </div>
          )}

          <div className="modal-actions">
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? activeTab === "login"
                  ? "Signing In..."
                  : "Creating Account..."
                : activeTab === "login"
                ? "Sign In"
                : "Create Account"}
            </button>
          </div>
        </form>

        <div className="modal-footer">
          {activeTab === "login" ? (
            <p>
              Don't have an account yet?{" "}
              <button
                type="button"
                className="link-btn"
                onClick={() => {
                  setActiveTab("register");
                  setFormErrors({});
                  clearAuthError();
                }}
              >
                Register now
              </button>
            </p>
          ) : (
            <p>
              Already registered?{" "}
              <button
                type="button"
                className="link-btn"
                onClick={() => {
                  setActiveTab("login");
                  setFormErrors({});
                  clearAuthError();
                }}
              >
                Sign in here
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

