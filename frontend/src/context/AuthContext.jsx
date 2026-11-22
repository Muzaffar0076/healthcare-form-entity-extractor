import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { fetchCsrfToken, getCsrfTokenFromCookie, getCurrentUser, loginUser, logoutUser, registerUser } from "../services/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Restore authenticated session on initial mount via HttpOnly cookie
  useEffect(() => {
    async function restoreSession() {
      try {
        const profile = await getCurrentUser();
        setUser(profile);
      } catch (err) {
        // Unauthenticated session - clean state
        setUser(null);
        // If an old session-bound CSRF token is lingering in cookies, refresh to anonymous binding
        const cookieToken = getCsrfTokenFromCookie();
        if (cookieToken && cookieToken.split(":")[2] !== "anon") {
          fetchCsrfToken().catch(() => {});
        }
      } finally {
        setIsLoading(false);
      }
    }

    restoreSession();
  }, []);

  const login = useCallback(async (email, password) => {
    setAuthError(null);
    try {
      const data = await loginUser({ email, password });
      setUser(data.user);
      return data;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const register = useCallback(async (formData) => {
    setAuthError(null);
    try {
      const data = await registerUser(formData);
      setUser(data.user);
      return data;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.warn("Logout API warning:", err.message);
    }
    setUser(null);
    setAuthError(null);
    fetchCsrfToken().catch(() => {});
  }, []);

  const clearAuthError = useCallback(() => {
    setAuthError(null);
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    authError,
    login,
    register,
    logout,
    clearAuthError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
