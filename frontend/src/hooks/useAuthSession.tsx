"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
//import { redisSessionManager, SessionData } from "@/lib/redis-session";

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

        // Get Supabase session token
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session?.access_token) {
          throw new Error("No valid session token");
        }

        // Get Redis session data
        //const sessionData = await redisSessionManager.getSession(
        //session.access_token
        //);
        setSessionData(sessionData);
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

  // const invalidateSession = async () => {
  //   try {
  //     const {
  //       data: { session },
  //     } = await supabase.auth.getSession();
  //     if (session?.access_token) {
  //       await redisSessionManager.invalidateSession(session.access_token);
  //     }
  //     setSessionData(null);
  //   } catch (error) {
  //     console.error("Failed to invalidate session:", error);
  //   }
  // };

  return {
    sessionData,
    sessionLoading,
    sessionError,
    invalidateSession,
    hasValidSession: !!sessionData,
  };
};
