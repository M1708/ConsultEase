"use client";

import { useState } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  isTyping?: boolean;
  placeholder?: string;
}

export const ChatInput = ({ onSendMessage, disabled, isTyping, placeholder }: ChatInputProps) => {
  const [message, setMessage] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex space-x-3">
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder || "Ask about clients, contracts, time tracking, deliverables, or employees..."}
        disabled={disabled}
        className="flex-1 resize-none border-2 border-blue-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 text-gray-900 placeholder-gray-500 text-base"
        style={{ fontFamily: 'Arial, sans-serif' }}
        rows={2}
      />
      <button
        type="submit"
        disabled={!message.trim() || disabled}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        style={{ fontFamily: 'Arial, sans-serif' }}
      >
        {isTyping ? (
          <div className="flex items-center space-x-1">
            <span>AI thinking</span>
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
              <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
            </div>
          </div>
        ) : (
          "Send"
        )}
      </button>
    </form>
  );
};
