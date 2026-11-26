import React, { useEffect, useRef } from "react";
import {
  User,
  LogOut,
  LogIn,
  UserPlus,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

/**
 * UserDropdown: Minimal account menu showing user identity,
 * direct profile access, and sign-out controls.
 */
export default function UserDropdown({
  isOpen,
  onClose,
  onNavigate,
  onOpenAuth,
  onOpenConsent,
}) {
  const { user, isAuthenticated, logout } = useAuth();
  const menuRef = useRef(null);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onClose();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleAction = (callback) => {
    onClose();
    if (callback) callback();
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
    <div
      ref={menuRef}
      className="user-dropdown-menu"
      role="menu"
      aria-label="User Account Menu"
    >
      {/* Profile Header: User identity info */}
      <div className="dropdown-user-header">
        <div className="dropdown-avatar-circle">
          {isAuthenticated ? (
            getInitials(user?.fullName, user?.email)
          ) : (
            <User size={16} />
          )}
        </div>
        <div className="dropdown-user-meta">
          <span className="dropdown-user-name">
            {isAuthenticated ? user?.fullName || "Account" : "Guest User"}
          </span>
          <span className="dropdown-user-email">
            {isAuthenticated ? user?.email : "Not signed in"}
          </span>
          {isAuthenticated && (
            <span className="dropdown-role-badge">{user?.role || "USER"}</span>
          )}
        </div>
      </div>

      <div className="dropdown-divider" />

      {/* Menu Options: Direct Profile access (not present in sidebar) */}
      {isAuthenticated && (
        <>
          <div className="dropdown-menu-items">
            <button
              type="button"
              role="menuitem"
              className="dropdown-item"
              onClick={() => handleAction(() => onNavigate("settings"))}
            >
              <User size={15} />
              <span>Profile</span>
            </button>
          </div>
          <div className="dropdown-divider" />
        </>
      )}

      {/* Footer Action: Logout / Login */}
      <div className="dropdown-footer">
        {isAuthenticated ? (
          <button
            type="button"
            role="menuitem"
            className="dropdown-item dropdown-item-danger"
            onClick={() => handleAction(logout)}
          >
            <LogOut size={15} />
            <span>Sign Out</span>
          </button>
        ) : (
          <div className="dropdown-auth-actions">
            <button
              type="button"
              className="btn btn-outline-sm btn-full"
              onClick={() => handleAction(() => onOpenAuth("login"))}
            >
              <LogIn size={14} />
              <span>Sign In</span>
            </button>
            <button
              type="button"
              className="btn btn-primary-sm btn-full"
              onClick={() => handleAction(() => onOpenAuth("register"))}
            >
              <UserPlus size={14} />
              <span>Create Account</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
