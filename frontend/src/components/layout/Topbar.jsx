import React, { useState } from "react";
import {
  Menu,
  Sparkles,
  ChevronRight,
  User,
  LayoutDashboard,
  Clock,
  Settings,
  HelpCircle,
  Sun,
  Moon,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import UserDropdown from "./UserDropdown";

/**
 * Topbar: Simplified top navigation with plain breadcrumbs,
 * theme toggle, primary action, and account dropdown.
 */
export default function Topbar({
  currentRoute = "dashboard",
  onRouteChange = () => {},
  onOpenMobileSidebar = () => {},
  onOpenAuth = () => {},
  onOpenConsent = () => {},
}) {
  const { user, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const routeMeta = {
    dashboard: {
      title: "Dashboard",
      parent: "Home",
      icon: LayoutDashboard,
    },
    "new-extraction": {
      title: "Extract Information",
      parent: "Document",
      icon: Sparkles,
    },
    history: {
      title: "Saved Documents",
      parent: "History",
      icon: Clock,
    },
    settings: {
      title: "Account & Preferences",
      parent: "Settings",
      icon: Settings,
    },
    help: {
      title: "Help & Guide",
      parent: "Help",
      icon: HelpCircle,
    },
  };

  const current = routeMeta[currentRoute] || routeMeta.dashboard;
  const CurrentIcon = current.icon;

  const getInitials = (name, email) => {
    if (name) {
      const parts = name.trim().split(" ");
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
      }
      return name.slice(0, 2).toUpperCase();
    }
    if (email) return email.slice(0, 2).toUpperCase();
    return "G";
  };

  return (
    <header className="saas-topbar">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="topbar-left">
        <button
          type="button"
          className="topbar-mobile-menu-btn"
          onClick={onOpenMobileSidebar}
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>

        <nav className="topbar-breadcrumbs" aria-label="Breadcrumb Navigation">
          <span
            className="breadcrumb-root"
            onClick={() => onRouteChange("dashboard")}
            role="button"
            tabIndex={0}
          >
            Healthcare Extractor
          </span>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <span className="breadcrumb-parent">{current.parent}</span>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <span className="breadcrumb-current">
            <CurrentIcon size={14} className="breadcrumb-icon" />
            <span>{current.title}</span>
          </span>
        </nav>
      </div>

      {/* Right: Quick Action, Theme Toggle & User Menu */}
      <div className="topbar-right">
        {/* Primary Action Button */}
        {currentRoute !== "new-extraction" && (
          <button
            type="button"
            className="btn btn-primary-sm topbar-cta-btn"
            onClick={() => onRouteChange("new-extraction")}
          >
            <Sparkles size={14} />
            <span>Extract Information</span>
          </button>
        )}

        {/* Theme Toggle Button */}
        <button
          type="button"
          className="topbar-theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? (
            <Sun size={17} className="theme-toggle-icon sun-icon" />
          ) : (
            <Moon size={17} className="theme-toggle-icon moon-icon" />
          )}
        </button>

        {/* User Profile Avatar */}
        <div className="topbar-user-section">
          <button
            type="button"
            className={`topbar-avatar-btn ${isDropdownOpen ? "active" : ""}`}
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            aria-expanded={isDropdownOpen}
            aria-haspopup="menu"
            title={isAuthenticated ? user?.email : "Guest Profile"}
          >
            <div className="topbar-avatar-circle">
              {isAuthenticated ? (
                getInitials(user?.fullName, user?.email)
              ) : (
                <User size={15} />
              )}
            </div>
          </button>

          <UserDropdown
            isOpen={isDropdownOpen}
            onClose={() => setIsDropdownOpen(false)}
            onNavigate={onRouteChange}
            onOpenAuth={onOpenAuth}
            onOpenConsent={onOpenConsent}
          />
        </div>
      </div>
    </header>
  );
}
