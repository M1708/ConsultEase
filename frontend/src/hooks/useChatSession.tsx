"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "./useAuth";
import { useChatStore } from "@/store/chatStore";
import { supabase } from "@/lib/supabase";
import { ChatMessage } from "@/types/chat";

// Simple chat session data interface for now
interface ChatSessionData {
  messages: ChatMessage[];
  sessionId: string;
  lastActivity: string;
}

export const useChatSession = () => {
  const { user, isAuthenticated } = useAuth();
  const { messages, sessionId, addMessage } = useChatStore();
  const [chatSessionLoading, setChatSessionLoading] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Auto-save chat session every 30 seconds
  useEffect(() => {
    if (!isAuthenticated || !user || messages.length === 0) return;

    const interval = setInterval(async () => {
      await saveChatSession();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [isAuthenticated, user, messages]);

  // Save on page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (messages.length > 0) {
        saveChatSession();
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [messages]);

  const saveChatSession = useCallback(async () => {
    if (!user || messages.length === 0) return;

    try {
      setChatSessionLoading(true);

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const chatData: ChatSessionData = {
        messages,
        sessionId,
        lastActivity: new Date().toISOString(),
      };

      // For now, just simulate success since Redis is not fully implemented
      const success = true;

      if (success) {
        setLastSaved(new Date());
      }
    } catch (error) {
      console.error("Failed to save chat session:", error);
    } finally {
      setChatSessionLoading(false);
    }
  }, [user, messages, sessionId]);

  const loadChatSession = useCallback(async () => {
    if (!user) return;

    // Don't block the UI - load session in background
    setChatSessionLoading(true);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      // For now, just simulate empty chat data since Redis is not fully implemented
      // No messages to restore in this simplified version
    } catch (error) {
      // Don't log errors in production to reduce noise
      if (process.env.NODE_ENV === 'development') {
        console.error("Failed to load chat session:", error);
      }
    } finally {
      setChatSessionLoading(false);
    }
  }, [user, sessionId, addMessage]);

  return {
    saveChatSession,
    loadChatSession,
    chatSessionLoading,
    lastSaved,
    hasSavedSession: !!lastSaved,
  };
};
