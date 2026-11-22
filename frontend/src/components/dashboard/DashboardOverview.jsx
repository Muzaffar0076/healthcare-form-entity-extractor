import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Pill,
  Calendar,
  Activity,
  FileText,
  Clock,
  ArrowRight,
  Eye,
  ShieldCheck,
  LogIn,
  RefreshCw,
  HelpCircle,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { fetchUserHistory, fetchHistoryDetail } from "../../services/historyApi";
import { formatDate } from "../../utils/formatters";
import StatCard from "./StatCard";
import HistoryDetailModal from "../HistoryDetailModal";

const SAMPLES = [
  {
    title: "Prescription Note",
    desc: "Prescription with Aspirin and diabetes reference.",
    text: "Patient was prescribed Aspirin on 12 March 2026 for diabetes.",
  },
  {
    title: "Doctor's Visit Note",
    desc: "Clinical note with acute pancreatitis and Metformin start date.",
    text: "The 45-year-old female presented with acute pancreatitis and was started on Metformin on 04 October 2024.",
  },
  {
    title: "Hospital Discharge Note",
    desc: "Discharge summary with pneumonia and Amoxicillin.",
    text: "Discharged on 15 January 2025 with resolution of bacterial pneumonia following treatment with Amoxicillin.",
  },
];

/**
 * DashboardOverview: High-level overview and document launcher.
 * Displays user's actual document counts and recent files in plain, accessible language.
 */
export default function DashboardOverview({
  onNavigate = () => {},
  onLoadText = () => {},
  onOpenAuth = () => {},
}) {
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState({
    totalExtractions: 0,
    medications: 0,
    dates: 0,
    conditions: 0,
  });
  const [recentRecords, setRecentRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Detail modal for viewing recent document
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  useEffect(() => {
    async function loadDashboardData() {
      if (!isAuthenticated) {
        setStats({
          totalExtractions: 0,
          medications: 0,
          dates: 0,
          conditions: 0,
        });
        setRecentRecords([]);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchUserHistory(1, 20);
        const items = data.items || [];
        const total = data.total || 0;

        let totalMeds = 0;
        let totalDates = 0;
        let totalConds = 0;

        items.forEach((item) => {
          if (item.entity_counts) {
            totalMeds += item.entity_counts.MEDICATION || 0;
            totalDates += item.entity_counts.DATE || 0;
            totalConds += item.entity_counts.CONDITION || 0;
          }
        });

        setStats({
          totalExtractions: total,
          medications: totalMeds,
          dates: totalDates,
          conditions: totalConds,
        });
        setRecentRecords(items.slice(0, 4));
      } catch (err) {
        setError(err.message || "Failed to load dashboard overview.");
      } finally {
        setIsLoading(false);
      }
    }

    loadDashboardData();
  }, [isAuthenticated]);

  const handleOpenDetail = async (recordId) => {
    setIsDetailLoading(true);
    try {
      const detail = await fetchHistoryDetail(recordId);
      setSelectedRecord(detail);
      setIsDetailModalOpen(true);
    } catch (err) {
      console.error("Failed to load record detail:", err);
    } finally {
      setIsDetailLoading(false);
    }
  };

  const handleLoadInWorkspace = (text) => {
    onLoadText(text);
    onNavigate("new-extraction");
  };

  return (
    <div className="dashboard-overview-page">
      {/* Welcome Banner */}
      <section className="dashboard-welcome-banner">
        <div className="welcome-text-wrap">
          <h1 className="welcome-title">
            Welcome, {isAuthenticated ? user?.fullName || "Navigator" : "Care Navigator"}
          </h1>
          <p className="welcome-subtitle">
            Easily locate medications, dates, and medical conditions in your healthcare documents.
          </p>
        </div>

        <div className="welcome-actions">
          <button
            type="button"
            className="btn btn-primary welcome-cta-btn"
            onClick={() => onNavigate("new-extraction")}
          >
            <Sparkles size={16} />
            <span>Extract New Document</span>
          </button>
        </div>
      </section>

      {/* Metrics Row */}
      <section className="dashboard-metrics-grid" aria-label="Document Statistics">
        <StatCard
          title="Documents Processed"
          value={stats.totalExtractions}
          subtitle={isAuthenticated ? "Saved in your account" : "Sign in to save documents"}
          icon={FileText}
          colorTheme="indigo"
          loading={isLoading}
        />
        <StatCard
          title="Medications Found"
          value={stats.medications}
          subtitle={isAuthenticated ? "Prescriptions and medicines" : "Saved document findings"}
          icon={Pill}
          colorTheme="emerald"
          loading={isLoading}
        />
        <StatCard
          title="Dates Found"
          value={stats.dates}
          subtitle={isAuthenticated ? "Appointments, visits, dates" : "Saved document findings"}
          icon={Calendar}
          colorTheme="blue"
          loading={isLoading}
        />
        <StatCard
          title="Conditions Found"
          value={stats.conditions}
          subtitle={isAuthenticated ? "Diagnoses and health issues" : "Saved document findings"}
          icon={Activity}
          colorTheme="rose"
          loading={isLoading}
        />
      </section>

      {/* Main 2-Column Content Grid */}
      <div className="dashboard-split-grid">
        {/* Left Column: Recent Documents */}
        <section className="dashboard-pane-recent">
          <div className="section-header-row">
            <div>
              <h2 className="section-title">Recent Documents</h2>
              <p className="section-description">
                Quick access to your previously analyzed healthcare documents.
              </p>
            </div>
            {isAuthenticated && recentRecords.length > 0 && (
              <button
                type="button"
                className="link-btn-text"
                onClick={() => onNavigate("history")}
              >
                <span>View all saved</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>

          {!isAuthenticated ? (
            <div className="saas-empty-panel">
              <div className="empty-panel-icon">
                <LogIn size={28} />
              </div>
              <h3 className="empty-panel-title">Sign in to Save Documents</h3>
              <p className="empty-panel-text">
                Create a free account to save your processed documents, review them anytime, and keep track of your findings.
              </p>
              <div className="empty-panel-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => onOpenAuth("login")}
                >
                  <LogIn size={15} />
                  <span>Sign In</span>
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => onNavigate("new-extraction")}
                >
                  <Sparkles size={15} />
                  <span>Try Without Account</span>
                </button>
              </div>
            </div>
          ) : isLoading ? (
            <div className="dashboard-loading-box">
              <RefreshCw size={24} className="spin-icon text-primary" />
              <span>Loading saved documents...</span>
            </div>
          ) : recentRecords.length === 0 ? (
            <div className="saas-empty-panel">
              <div className="empty-panel-icon">
                <FileText size={28} />
              </div>
              <h3 className="empty-panel-title">No Saved Documents Yet</h3>
              <p className="empty-panel-text">
                Upload a medical PDF or paste text to extract your first healthcare document.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => onNavigate("new-extraction")}
              >
                <Sparkles size={15} />
                <span>Extract First Document</span>
              </button>
            </div>
          ) : (
            <div className="recent-records-list">
              {recentRecords.map((rec) => (
                <div key={rec.id} className="recent-record-card">
                  <div className="recent-record-top">
                    <span className="recent-record-date">
                      <Clock size={13} />
                      <span>{formatDate(rec.created_at)}</span>
                    </span>
                    <div className="recent-record-actions">
                      <button
                        type="button"
                        className="btn-icon-subtle"
                        onClick={() => handleOpenDetail(rec.id)}
                        disabled={isDetailLoading}
                        title="View document details"
                        aria-label="View document details"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        type="button"
                        className="btn-text-subtle"
                        onClick={() => handleLoadInWorkspace(rec.form_text_preview)}
                        title="Open this document in the extractor"
                      >
                        <span>Open Document</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>

                  <p className="recent-record-snippet">
                    "{rec.form_text_preview}"
                  </p>

                  <div className="recent-record-pills">
                    {rec.entity_counts?.MEDICATION ? (
                      <span className="tag-pill tag-med">
                        {rec.entity_counts.MEDICATION} Medication{rec.entity_counts.MEDICATION > 1 ? "s" : ""}
                      </span>
                    ) : null}
                    {rec.entity_counts?.DATE ? (
                      <span className="tag-pill tag-date">
                        {rec.entity_counts.DATE} Date{rec.entity_counts.DATE > 1 ? "s" : ""}
                      </span>
                    ) : null}
                    {rec.entity_counts?.CONDITION ? (
                      <span className="tag-pill tag-cond">
                        {rec.entity_counts.CONDITION} Condition{rec.entity_counts.CONDITION > 1 ? "s" : ""}
                      </span>
                    ) : null}
                    {rec.total_entities === 0 && (
                      <span className="tag-pill tag-neutral">0 items</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Right Column: Sample Documents & Information Guide */}
        <aside className="dashboard-pane-sidebar">
          {/* Quick Sample Documents */}
          <div className="dashboard-side-card">
            <div className="side-card-header">
              <Sparkles size={16} className="text-primary" />
              <h3 className="side-card-title">Try a Sample Document</h3>
            </div>
            <p className="side-card-description">
              Select an example to see how the extractor highlights key information automatically.
            </p>

            <div className="sample-template-list">
              {SAMPLES.map((sample, idx) => (
                <div
                  key={idx}
                  className="sample-template-item"
                  onClick={() => handleLoadInWorkspace(sample.text)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handleLoadInWorkspace(sample.text);
                    }
                  }}
                  title="Click to load into the extractor"
                >
                  <div className="sample-item-info">
                    <span className="sample-item-title">{sample.title}</span>
                    <span className="sample-item-desc">{sample.desc}</span>
                  </div>
                  <ArrowRight size={14} className="sample-item-arrow" />
                </div>
              ))}
            </div>
          </div>

          {/* Simple Guide: What We Detect (Replacing the developer-focused Model Specs card) */}
          <div className="dashboard-side-card">
            <div className="side-card-header">
              <HelpCircle size={16} className="text-primary" />
              <h3 className="side-card-title">What This Tool Finds</h3>
            </div>
            <div className="specs-list">
              <div className="spec-item">
                <span className="spec-label">Medications</span>
                <span className="spec-value">Prescriptions & dosages</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Dates</span>
                <span className="spec-value">Appointments & visits</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Conditions</span>
                <span className="spec-value">Diagnoses & symptoms</span>
              </div>
            </div>
          </div>

          {/* Privacy & Confidentiality Card */}
          <div className="dashboard-side-card privacy-side-card">
            <div className="side-card-header">
              <ShieldCheck size={16} className="text-emerald" />
              <h3 className="side-card-title">Your Privacy Matters</h3>
            </div>
            <p className="side-card-description">
              Your documents are analyzed to extract information and are only saved to your account if you choose to save them. Your documents are never shared publicly.
            </p>
          </div>
        </aside>
      </div>

      {/* History Detail Modal */}
      <HistoryDetailModal
        isOpen={isDetailModalOpen}
        record={selectedRecord}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedRecord(null);
        }}
        onDelete={() => {
          setIsDetailModalOpen(false);
          setSelectedRecord(null);
        }}
      />
    </div>
  );
}
