import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

/**
 * DashboardLayout: The master shell component providing the 3-section layout:
 * - Left Sidebar (Desktop collapsible & Mobile responsive drawer)
 * - Persistent Topbar (Breadcrumbs, Theme Toggle & User Dropdown)
 * - Flexible Main Content Area
 */
export default function DashboardLayout({
  currentRoute = "dashboard",
  onRouteChange = () => {},
  onOpenAuth = () => {},
  onOpenConsent = () => {},
  children,
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className={`saas-dashboard-shell ${isCollapsed ? "sidebar-collapsed" : ""}`}>
      {/* Sidebar Navigation */}
      <Sidebar
        currentRoute={currentRoute}
        onRouteChange={onRouteChange}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        onOpenAuth={onOpenAuth}
      />

      {/* Main Workspace Frame */}
      <div className="saas-main-frame">
        {/* Topbar Navigation */}
        <Topbar
          currentRoute={currentRoute}
          onRouteChange={onRouteChange}
          onOpenMobileSidebar={() => setIsMobileOpen(true)}
          onOpenAuth={onOpenAuth}
          onOpenConsent={onOpenConsent}
        />

        {/* Scrollable Content Canvas */}
        <main className="saas-content-canvas" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
