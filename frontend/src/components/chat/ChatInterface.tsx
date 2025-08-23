// frontend/components/chat/ChatInterface.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { Button } from "@/components/ui/Button";
import { UserProfile } from "@/components/UserProfile";
import { RefreshCw, MessageSquare, AlertCircle } from "lucide-react";

export const ChatInterface = () => {
  const { user } = useAuth();
  const {
    messages,
    isTyping,
    error,
    sendMessage,
    clearChat,
    clearError,
    hasMessages,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showWelcome, setShowWelcome] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Hide welcome message when user sends first message
  useEffect(() => {
    if (hasMessages) {
      setShowWelcome(false);
    }
  }, [hasMessages]);

  const handleSendMessage = async (message: string) => {
    setShowWelcome(false);
    await sendMessage(message);
  };

  const welcomeMessages = [
    "👋 Hello! I'm your ConsultEase AI assistant.",
    "I can help you with:",
    "• Client management and onboarding",
    "• Contract creation and tracking",
    "• Project deliverables and milestones",
    "• Time tracking and productivity",
    "• Generating reports and insights",
    "",
    "What would you like to work on today?",
  ];

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Authentication Required
          </h3>
          <p className="text-gray-600">
            Please log in to access the chat interface.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
              <MessageSquare className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                ConsultEase AI Assistant
              </h1>
              <p className="text-sm text-gray-600">
                Your intelligent business companion
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {hasMessages && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearChat}
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                New Chat
              </Button>
            )}
            <UserProfile />
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Welcome Message */}
        {showWelcome && !hasMessages && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="text-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Welcome, {user.first_name || user.email}!
                </h2>
                <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {user.role.replace("_", " ").toUpperCase()} •{" "}
                  {user.status.toUpperCase()}
                </div>
              </div>

              <div className="space-y-2 text-sm text-gray-700">
                {welcomeMessages.map((message, index) => (
                  <div key={index} className={message === "" ? "h-2" : ""}>
                    {message}
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    handleSendMessage("Show me my recent activity")
                  }
                >
                  Recent Activity
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSendMessage("List all clients")}
                >
                  View Clients
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    handleSendMessage("What can you help me with?")
                  }
                >
                  Learn More
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="max-w-2xl mx-auto mb-4">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Something went wrong</p>
                <p className="text-sm mt-1">{error}</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={clearError}
                  className="mt-2"
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="max-w-4xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {/* Typing Indicator */}
          {isTyping && <TypingIndicator />}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={isTyping}
            placeholder={
              user.role === "client"
                ? "Ask about your projects, contracts, or billing..."
                : "Ask me about clients, contracts, deliverables, time tracking..."
            }
          />

          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <div>Press Enter to send, Shift+Enter for new line</div>
            <div>
              Session:{" "}
              {messages.length > 0 ? messages[0].session_id.slice(-8) : "New"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
