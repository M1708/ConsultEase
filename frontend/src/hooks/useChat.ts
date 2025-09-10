import { useChatStore } from "@/store/chatStore";
import { useCallback } from "react";

export const useChat = () => {
  const {
    messages,
    isTyping,
    error,
    sessionId,
    sendMessage,
    clearMessages,
    setTyping,
    addMessage,
    clearError,
    setMessages,
  } = useChatStore();

  const handleSendMessage = useCallback(
    async (message: string, displayMessage?: string) => {
      if (!message.trim()) return;

      try {
        await sendMessage(message.trim(), displayMessage);
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [sendMessage]
  );

  const handleClearChat = useCallback(() => {
    clearMessages();
    clearError();
  }, [clearMessages, clearError]);

  return {
    messages,
    isTyping,
    error,
    sessionId,
    sendMessage: handleSendMessage,
    clearChat: handleClearChat,
    clearError,
    setTyping,
    setMessages,
    // Computed properties
    hasMessages: messages.length > 0,
    lastMessage: messages[messages.length - 1] || null,
    userMessages: messages.filter((m) => m.isUser),
    agentMessages: messages.filter((m) => !m.isUser),
  };
};
