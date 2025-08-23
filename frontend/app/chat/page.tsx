"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { useChatSession } from "@/hooks/useChatSession";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ChatSessionStatus } from "@/components/chat/ChatSessionStatus";
import { ChatInput } from "@/components/chat/ChatInput";
import { useAuthStore } from "@/store/authStore";

export default function ChatPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { messages, isTyping, error, sendMessage, clearChat, clearError } =
    useChat();

  const { loadChatSession, saveChatSession } = useChatSession();

  // Load chat session on mount
  useEffect(() => {
    loadChatSession();
  }, [loadChatSession]);

  useEffect(() => {
    const authState = useAuthStore.getState();
    console.log("Session ID:", authState.sessionId);
  }, []);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    try {
      await sendMessage(message);
      // Auto-save after sending message
      await saveChatSession();
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleLogout = async () => {
    try {
      // Save chat session before logout
      await saveChatSession();
      await logout();
      router.push("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">
                  ConsultEase AI Assistant
                </h1>
              </div>

              <div className="flex items-center space-x-4">
                <ChatSessionStatus />

                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    {user?.full_name || user?.email}
                  </span>
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    {user?.role}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Chat Interface */}
        <main className="max-w-4xl mx-auto p-4">
          <div className="bg-white rounded-lg shadow h-[calc(100vh-8rem)] flex flex-col">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <h3 className="text-lg font-medium mb-2">
                    Welcome to ConsultEase AI Assistant
                  </h3>
                  <p>
                    Ask me anything about your clients, contracts, time
                    tracking, or deliverables.
                  </p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        message.isUser
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      {!message.isUser && (
                        <div className="text-xs text-gray-600 mb-1">
                          {message.agent}
                        </div>
                      )}
                      <div className="whitespace-pre-wrap">
                        {message.isUser ? message.message : message.response}
                      </div>
                      <div className="text-xs mt-1 opacity-70">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}

              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                    <div className="flex items-center space-x-1">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="px-4 py-2 bg-red-50 border-t border-red-200">
                <div className="flex justify-between items-center">
                  <span className="text-red-700 text-sm">{error}</span>
                  <button
                    onClick={clearError}
                    className="text-red-700 hover:text-red-900"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}

            {/* Input Area */}
            <div className="border-t p-4">
              <ChatInput
                onSendMessage={handleSendMessage}
                disabled={isTyping}
              />

              <div className="flex justify-between items-center mt-2">
                <button
                  onClick={clearChat}
                  className="text-xs text-gray-500 hover:text-gray-700"
                >
                  Clear conversation
                </button>

                <div className="text-xs text-gray-500">
                  {messages.filter((m) => !m.isUser).length} AI responses
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
