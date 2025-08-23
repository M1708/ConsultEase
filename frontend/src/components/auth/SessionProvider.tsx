"use client";

import { createContext, useContext, ReactNode } from "react";

interface SessionContextType {
  sessionData: null;
  sessionLoading: boolean;
  sessionError: string | null;
  invalidateSession: () => Promise<void>;
  hasValidSession: boolean;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};

interface SessionProviderProps {
  children: ReactNode;
}

export const SessionProvider = ({ children }: SessionProviderProps) => {
  // Minimal session data - no hooks for now
  const sessionData = {
    sessionData: null,
    sessionLoading: false,
    sessionError: null,
    invalidateSession: async () => {},
    hasValidSession: true, // Always true for now
  };

  return (
    <SessionContext.Provider value={sessionData}>
      {children}
    </SessionContext.Provider>
  );
};
