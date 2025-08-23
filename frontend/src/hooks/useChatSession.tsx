"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "./useAuth";
import { useChatStore } from "@/store/chatStore";
//import { redisSessionManager, ChatSessionData } from "@/lib/redis-session";
import { supabase } from "@/lib/supabase";

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

      // const success = await redisSessionManager.storeChatSession(
      //   sessionId,
      //   user.user_id,
      //   chatData,
      //   session.access_token
      // );

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

    try {
      setChatSessionLoading(true);

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      // const chatData = await redisSessionManager.getChatSession(
      //   sessionId,
      //   user.user_id,
      //   session.access_token
      // );

      if (chatData?.messages) {
        // Restore messages to chat store
        chatData.messages.forEach((message) => {
          addMessage(message);
        });
      }
    } catch (error) {
      console.error("Failed to load chat session:", error);
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
