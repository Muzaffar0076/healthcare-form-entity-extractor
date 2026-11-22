import React from "react";
import {
  Activity,
  LayoutDashboard,
  Sparkles,
  Clock,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  LogIn,
  User,
  X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

/**
 * Sidebar: Simplified, distraction-free navigation drawer.
 * Technical ML badges and developer tags have been removed.
 */
export default function Sidebar({
  currentRoute = "dashboard",
  onRouteChange = () => {},
  isCollapsed = false,
  onToggleCollapse = () => {},
  isMobileOpen = false,
  onCloseMobile = () => {},
  onOpenAuth = () => {},
}) {
  const { user, isAuthenticated } = useAuth();

  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      id: "new-extraction",
      label: "Extract Information",
      icon: Sparkles,
    },
    {
      id: "history",
      label: "Saved Documents",
      icon: Clock,
      authRequired: true,
    },
  ];

  const secondaryItems = [
    {
      id: "settings",
      label: "Settings",
      icon: Settings,
    },
    {
      id: "help",
      label: "Help & Guide",
      icon: HelpCircle,
    },
  ];

  const handleNavClick = (id) => {
    onRouteChange(id);
    if (isMobileOpen) {
      onCloseMobile();
    }
  };

  const getInitials = (name, email) => {
    if (name) {
      const parts = name.trim().split(" ");
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
      }
      return name.slice(0, 2).toUpperCase();
    }
    if (email) return email.slice(0, 2).toUpperCase();
    return "U";
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`saas-sidebar ${isCollapsed ? "collapsed" : ""} ${
          isMobileOpen ? "mobile-open" : ""
        }`}
        aria-label="Application Navigation"
      >
        {/* Brand & Logo Header */}
        <div className="sidebar-brand-header">
          <div
            className="brand-logo-wrap"
            onClick={() => handleNavClick("dashboard")}
            role="button"
            tabIndex={0}
            title="Healthcare Form Extractor"
          >
            <div className="brand-icon-box">
              <Activity size={20} className="brand-icon" />
            </div>
            {!isCollapsed && (
              <div className="brand-text-group">
                <span className="brand-title">Healthcare</span>
                <span className="brand-subtitle">Form Extractor</span>
              </div>
            )}
          </div>

          {/* Desktop Collapse Toggle */}
          <button
            type="button"
            className="sidebar-collapse-btn desktop-only"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>

          {/* Mobile Close Button */}
          <button
            type="button"
            className="sidebar-close-btn mobile-only"
            onClick={onCloseMobile}
            aria-label="Close navigation drawer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Primary Navigation Section */}
        <div className="sidebar-nav-scroll">
          <div className="sidebar-nav-group">
            {!isCollapsed && <span className="nav-section-label">MAIN</span>}
            <nav className="nav-list">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = currentRoute === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`nav-item ${isActive ? "active" : ""}`}
                    onClick={() => {
                      if (item.authRequired && !isAuthenticated) {
                        onOpenAuth("login");
                      } else {
                        handleNavClick(item.id);
                      }
                    }}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <Icon size={18} className="nav-item-icon" />
                    {!isCollapsed && (
                      <span className="nav-item-label">{item.label}</span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="sidebar-nav-group">
            {!isCollapsed && <span className="nav-section-label">ACCOUNT & HELP</span>}
            <nav className="nav-list">
              {secondaryItems.map((item) => {
                const Icon = item.icon;
                const isActive = currentRoute === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`nav-item ${isActive ? "active" : ""}`}
                    onClick={() => handleNavClick(item.id)}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <Icon size={18} className="nav-item-icon" />
                    {!isCollapsed && <span className="nav-item-label">{item.label}</span>}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Bottom User Profile Section */}
        <div className="sidebar-footer">
          {isAuthenticated ? (
            <div className="sidebar-user-card" title={user?.email}>
              <div className="sidebar-user-avatar">
                {getInitials(user?.fullName, user?.email)}
              </div>
              {!isCollapsed && (
                <div className="sidebar-user-info">
                  <span className="sidebar-user-name">{user?.fullName || "User"}</span>
                  <span className="sidebar-user-role">{user?.role || "USER"}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="sidebar-guest-card">
              {!isCollapsed ? (
                <button
                  type="button"
                  className="btn btn-primary-sm btn-full"
                  onClick={() => onOpenAuth("login")}
                >
                  <LogIn size={14} />
                  <span>Sign In</span>
                </button>
              ) : (
                <button
                  type="button"
                  className="sidebar-guest-icon-btn"
                  onClick={() => onOpenAuth("login")}
                  title="Sign In"
                >
                  <User size={18} />
                </button>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
