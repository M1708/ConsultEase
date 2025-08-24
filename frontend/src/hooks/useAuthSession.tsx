"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";

// Simple session data interface for now
interface SessionData {
  sessionId: string;
  userId: string;
  email: string;
  role: string;
  createdAt: string;
  lastAccessed: string;
}

export const useAuthSession = () => {
  const { user, isAuthenticated } = useAuth();
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    const loadSession = async () => {
      if (!isAuthenticated || !user) {
        setSessionLoading(false);
        return;
      }

      try {
        setSessionLoading(true);
        setSessionError(null);

        // For now, create a simple session data object
        const mockSessionData: SessionData = {
          sessionId: "mock-session",
          userId: user.user_id,
          email: user.email,
          role: user.role,
          createdAt: new Date().toISOString(),
          lastAccessed: new Date().toISOString(),
        };

        setSessionData(mockSessionData);
      } catch (error) {
        console.error("Session load error:", error);
        setSessionError(
          error instanceof Error ? error.message : "Session load failed"
        );
      } finally {
        setSessionLoading(false);
      }
    };

    loadSession();
  }, [isAuthenticated, user]);

  const invalidateSession = async () => {
    try {
      setSessionData(null);
    } catch (error) {
      console.error("Failed to invalidate session:", error);
    }
  };

  return {
    sessionData,
    sessionLoading,
    sessionError,
    invalidateSession,
    hasValidSession: !!sessionData,
  };
};
