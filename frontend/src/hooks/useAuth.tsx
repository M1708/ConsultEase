"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/store/authStore";

export const useAuth = () => {
  const {
    isAuthenticated,
    user,
    loading,
    error,
    login,
    logout,
    initialize,
    clearError,
    updateUser,
  } = useAuthStore();

  // Add this debug logging (only in development)
  if (process.env.NODE_ENV === 'development') {
    console.log("useAuth state:", {
      isAuthenticated,
      user: user?.email,
      loading,
      error,
    });
  }

  useEffect(() => {
    // Only initialize if not already authenticated to prevent redundant calls
    if (!isAuthenticated && !loading) {
      initialize();
    }
  }, [initialize, isAuthenticated, loading]);

  return {
    isAuthenticated,
    user,
    loading,
    error,
    login,
    logout,
    clearError,
    updateUser,
    // Computed properties
    isAdmin: user?.role === "super_admin" || user?.role === "admin",
    isManager: user?.role === "manager",
    isEmployee: user?.role === "employee",
    isClient: user?.role === "client",
    canManageUsers: user?.role === "super_admin" || user?.role === "admin",
    canViewReports: user?.role !== "viewer" && user?.role !== "client",
  };
};
