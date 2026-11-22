import React, { useState, useEffect, useCallback } from "react";
import { CheckCircle2 } from "lucide-react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import DashboardLayout from "./components/layout/DashboardLayout";
import DashboardOverview from "./components/dashboard/DashboardOverview";
import ExtractionWorkspace from "./components/workspace/ExtractionWorkspace";
import HistoryView from "./components/HistoryView";
import SettingsView from "./components/views/SettingsView";
import HelpView from "./components/views/HelpView";
import AuthModal from "./components/AuthModal";
import ConsentModal from "./components/ConsentModal";
import { fetchCsrfToken, ensureCsrfToken } from "./services/authApi";
import { saveExtractionHistory } from "./services/historyApi";
import { API_BASE } from "./services/apiConfig";

function MainDashboard() {
  const { user, isAuthenticated } = useAuth();

  // Navigation route: "dashboard" | "new-extraction" | "history" | "settings" | "help"
  const [currentRoute, setCurrentRoute] = useState("dashboard");

  // Extraction Workbench State
  const [inputMode, setInputMode] = useState("text"); // "text" | "pdf"
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Synchronized entity selection state
  const [selectedEntityIndex, setSelectedEntityIndex] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const [toastMessage, setToastMessage] = useState(null);

  // History & Consent states
  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false);
  const [isSavingHistory, setIsSavingHistory] = useState(false);
  const [savedRecordId, setSavedRecordId] = useState(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState(null);

  // Auth modal state
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState("login");

  // Internal backend health check (not exposed to user-facing UI)
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .catch(() => {});
  }, []);

  // Redirect to dashboard if logged-out user is on private history page
  useEffect(() => {
    if (!isAuthenticated && currentRoute === "history") {
      setCurrentRoute("dashboard");
    }
  }, [isAuthenticated, currentRoute]);

  const openAuthModal = (tab = "login") => {
    setAuthModalTab(tab);
    setIsAuthModalOpen(true);
  };

  const getConsentKey = () =>
    user?._id ? `extraction_consent_${user._id}` : "extraction_consent_default";

  const hasUserConsent = () => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(getConsentKey()) === "granted";
  };

  const handlePDFExtractionSuccess = (data) => {
    setResult(data);
    setError(null);
    setSavedRecordId(null);
    setSaveSuccessMessage(null);
    setSelectedEntityIndex(null);
    const count = data.entities ? data.entities.length : 0;
    setAnnouncement(`PDF processed. Found ${count} items.`);
  };

  const handleSaveToHistory = async () => {
    if (!result || !result.text || !isAuthenticated) return;

    if (!hasUserConsent()) {
      setIsConsentModalOpen(true);
      return;
    }

    setIsSavingHistory(true);
    setError(null);
    try {
      const payload = {
        form_text: result.text,
        extracted_entities: {
          entities: result.entities || [],
        },
      };
      const saved = await saveExtractionHistory(payload);
      setSavedRecordId(saved.id);
      setSaveSuccessMessage("Saved to your documents!");
      setAnnouncement("Document saved to your history.");
      setToastMessage("Document saved to your history!");
      setTimeout(() => {
        setSaveSuccessMessage(null);
        setToastMessage(null);
      }, 3500);
    } catch (err) {
      setError(err.message || "Failed to save document.");
    } finally {
      setIsSavingHistory(false);
    }
  };

  const handleConsentConfirm = async () => {
    if (typeof window !== "undefined") {
      localStorage.setItem(getConsentKey(), "granted");
    }
    setIsConsentModalOpen(false);
    if (result && result.text && isAuthenticated) {
      await handleSaveToHistory();
    }
  };

  const handleExtract = async () => {
    const trimmed = inputText.trim();
    if (!trimmed) {
      setError("Please enter or paste healthcare document text before extracting.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setSavedRecordId(null);
    setSaveSuccessMessage(null);
    setSelectedEntityIndex(null);

    try {
      let csrfToken = null;
      try {
        csrfToken = await ensureCsrfToken();
      } catch {
        // Fallback if CSRF endpoint unneeded for anonymous
      }

      const headers = { "Content-Type": "application/json" };
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }

      let response = await fetch(`${API_BASE}/api/v1/extract`, {
        method: "POST",
        credentials: "include",
        headers,
        body: JSON.stringify({ text: trimmed }),
      });

      // Self-healing: if rejected due to stale CSRF token, force fresh token and retry once
      if (response.status === 403) {
        const errData = await response.clone().json().catch(() => ({}));
        if (errData.message && errData.message.toLowerCase().includes("csrf")) {
          try {
            csrfToken = await fetchCsrfToken();
            if (csrfToken) {
              headers["X-CSRF-Token"] = csrfToken;
            }
            response = await fetch(`${API_BASE}/api/v1/extract`, {
              method: "POST",
              credentials: "include",
              headers,
              body: JSON.stringify({ text: trimmed }),
            });
          } catch {
            // Retain original response if retry fails
          }
        }
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || `Server error (${response.status})`);
      }

      setResult(data);
      const count = data.entities ? data.entities.length : 0;
      setAnnouncement(`Document processed. Found ${count} items.`);
    } catch (err) {
      setError(err.message || "Unable to extract information right now. Please check your connection and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setInputText("");
    setResult(null);
    setError(null);
    setSavedRecordId(null);
    setSaveSuccessMessage(null);
    setSelectedEntityIndex(null);
    setAnnouncement("Input cleared.");
  };

  const handleLoadTextFromDashboard = useCallback((text) => {
    setInputText(text);
    setInputMode("text");
    setResult(null);
    setError(null);
    setSavedRecordId(null);
    setSaveSuccessMessage(null);
    setSelectedEntityIndex(null);
  }, []);

  return (
    <DashboardLayout
      currentRoute={currentRoute}
      onRouteChange={setCurrentRoute}
      onOpenAuth={openAuthModal}
      onOpenConsent={() => setIsConsentModalOpen(true)}
    >
      {/* Route Views */}
      {currentRoute === "dashboard" && (
        <DashboardOverview
          onNavigate={setCurrentRoute}
          onLoadText={handleLoadTextFromDashboard}
          onOpenAuth={openAuthModal}
        />
      )}

      {currentRoute === "new-extraction" && (
        <ExtractionWorkspace
          inputText={inputText}
          setInputText={setInputText}
          inputMode={inputMode}
          setInputMode={setInputMode}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
          result={result}
          setResult={setResult}
          error={error}
          setError={setError}
          selectedEntityIndex={selectedEntityIndex}
          setSelectedEntityIndex={setSelectedEntityIndex}
          onExtract={handleExtract}
          onClear={handleClear}
          onPDFSuccess={handlePDFExtractionSuccess}
          onSaveToHistory={handleSaveToHistory}
          isSavingHistory={isSavingHistory}
          savedRecordId={savedRecordId}
          saveSuccessMessage={saveSuccessMessage}
          setAnnouncement={setAnnouncement}
          setToastMessage={setToastMessage}
        />
      )}

      {currentRoute === "history" && isAuthenticated && (
        <HistoryView onOpenConsentModal={() => setIsConsentModalOpen(true)} />
      )}

      {currentRoute === "settings" && (
        <SettingsView onOpenConsent={() => setIsConsentModalOpen(true)} />
      )}

      {currentRoute === "help" && <HelpView />}

      {/* Screen Reader Live Announcements */}
      <div className="visually-hidden" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      {/* Floating Action/Copy Toast Notification */}
      {toastMessage && (
        <div className="toast-notification" role="status">
          <CheckCircle2 size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialTab={authModalTab}
      />

      {/* Consent Modal */}
      <ConsentModal
        isOpen={isConsentModalOpen}
        onClose={() => setIsConsentModalOpen(false)}
        onConfirm={handleConsentConfirm}
      />
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <MainDashboard />
      </AuthProvider>
    </ThemeProvider>
  );
}
