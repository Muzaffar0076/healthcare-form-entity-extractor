import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  FileUp,
} from "lucide-react";
import { getCsrfTokenFromCookie, fetchCsrfToken } from "../services/authApi";
import { formatFileSize } from "../utils/formatters";
import { API_BASE } from "../services/apiConfig";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export default function PDFUploader({ onExtractionSuccess, isLoading, setIsLoading }) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const fileInputRef = useRef(null);

  const validateAndSetFile = (file) => {
    setError(null);
    if (!file) return;

    // 1. File extension validation
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".pdf")) {
      setError("Invalid file type. Only PDF documents (.pdf) are supported.");
      setSelectedFile(null);
      return;
    }

    // 2. MIME type validation (allow empty if browser doesn't detect, but reject non-pdf MIME)
    if (file.type && file.type !== "application/pdf" && file.type !== "application/x-pdf") {
      setError("Invalid file format. Please select an authentic PDF document.");
      setSelectedFile(null);
      return;
    }

    // 3. File size validation (10 MB ceiling)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError(`File is too large (${formatFileSize(file.size)}). Maximum allowed size is 10 MB.`);
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setError("The selected PDF file is empty (0 bytes).");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadProgress(0);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadAndExtract = async () => {
    if (!selectedFile) {
      setError("Please select a healthcare PDF document first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setUploadProgress(25);

    try {
      let csrfToken = getCsrfTokenFromCookie();
      if (!csrfToken) {
        try {
          csrfToken = await fetchCsrfToken();
        } catch {
          // Anonymous requests may not require CSRF
        }
      }

      const formData = new FormData();
      formData.append("file", selectedFile);

      setUploadProgress(50);

      const headers = {};
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }

      let response = await fetch(`${API_BASE}/api/v1/extract/pdf`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
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
            response = await fetch(`${API_BASE}/api/v1/extract/pdf`, {
              method: "POST",
              credentials: "include",
              headers,
              body: formData,
            });
          } catch {
            // Retain original response if retry fails
          }
        }
      }

      setUploadProgress(85);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.detail || `Server error (${response.status})`);
      }

      setUploadProgress(100);
      onExtractionSuccess(data);
    } catch (err) {
      setError(err.message || "Failed to process PDF document.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="pdf-uploader-container">
      {/* Drop Zone */}
      <div
        className={`pdf-dropzone ${dragOver ? "drag-over" : ""} ${selectedFile ? "has-file" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !selectedFile && fileInputRef.current?.click()}
        tabIndex={!selectedFile ? 0 : undefined}
        role={!selectedFile ? "button" : undefined}
        aria-label={!selectedFile ? "Upload Healthcare PDF Document: Drag and drop or press to browse files" : "Selected PDF file"}
        onKeyDown={(e) => {
          if (!selectedFile && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
      >
        <label htmlFor="pdf-file-upload-input" className="visually-hidden">
          Upload Healthcare PDF Document
        </label>
        <input
          id="pdf-file-upload-input"
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: "none" }}
          onChange={handleFileInputChange}
        />

        {!selectedFile ? (
          <div className="dropzone-content">
            <div className="dropzone-icon-circle">
              <UploadCloud size={32} />
            </div>
            <h3>Drag & Drop Healthcare PDF Here</h3>
            <p className="dropzone-sub">
              or <span className="browse-link">browse files</span> from your computer
            </p>
            <div className="dropzone-hint">
              Supports intake forms, prescriptions, and lab reports up to 10 MB
            </div>
          </div>
        ) : (
          <div className="selected-file-card" onClick={(e) => e.stopPropagation()}>
            <div className="file-info-group">
              <div className="file-icon-badge">
                <FileText size={24} />
              </div>
              <div className="file-meta">
                <span className="file-name" title={selectedFile.name}>
                  {selectedFile.name}
                </span>
                <span className="file-size">{formatFileSize(selectedFile.size)}</span>
              </div>
            </div>

            <button
              type="button"
              className="btn-remove-file"
              onClick={handleRemoveFile}
              title="Remove file"
              disabled={isLoading}
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Upload Progress Bar */}
      {isLoading && (
        <div className="upload-progress-box">
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <span className="progress-label">
            {uploadProgress < 50
              ? "Uploading document..."
              : uploadProgress < 85
              ? "Parsing text with PyMuPDF & extracting entities..."
              : "Finalizing entity recognition..."}
          </span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="button-bar" style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!selectedFile || isLoading}
          onClick={handleUploadAndExtract}
        >
          <Sparkles size={16} />
          <span>{isLoading ? "Extracting Entities..." : "Upload and Extract"}</span>
        </button>

        {selectedFile && !isLoading && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRemoveFile}
          >
            Clear File
          </button>
        )}
      </div>
    </div>
  );
}

