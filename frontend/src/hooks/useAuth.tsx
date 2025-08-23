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

  // Add this debug logging
  console.log("useAuth state:", {
    isAuthenticated,
    user: user?.email,
    loading,
    error,
  });

  useEffect(() => {
    initialize();
  }, [initialize]);

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
