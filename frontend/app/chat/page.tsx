"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { useChatSession } from "@/hooks/useChatSession";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ChatInput } from "@/components/chat/ChatInput";
import { TypewriterText } from "@/components/chat/TypewriterText";
import { useAuthStore } from "@/store/authStore";
import { Upload, Clock, MessageSquare, FileText, X, Wifi, WifiOff } from "lucide-react";

export default function ChatPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { messages, isTyping, sendMessage, clearChat } = useChat();
  const { loadChatSession, saveChatSession } = useChatSession();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [redisStatus, setRedisStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const [sessionWarning, setSessionWarning] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat session on mount (non-blocking)
  useEffect(() => {
    // Load session in background without blocking UI
    setTimeout(() => {
      loadChatSession();
    }, 100); // Small delay to let UI render first
  }, [loadChatSession]);

  useEffect(() => {
    const authState = useAuthStore.getState();
    console.log("Session ID:", authState.sessionId);
    
    // Check Redis connection status
    const checkRedisStatus = async () => {
      try {
        const token = localStorage.getItem("supabase_token");
        if (token) {
          // Simple ping to check if Redis is accessible
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/chat/health`);
          if (response.ok) {
            setRedisStatus('connected');
          } else {
            setRedisStatus('disconnected');
          }
        } else {
          setRedisStatus('disconnected');
        }
      } catch (error) {
        console.warn("Redis status check failed:", error);
        setRedisStatus('disconnected');
      }
    };
    
    checkRedisStatus();
    // Check status every 30 seconds
    const interval = setInterval(checkRedisStatus, 30000);
    
    // Check session expiry
    const checkSessionExpiry = () => {
      const token = localStorage.getItem("supabase_token");
      if (token) {
        try {
          // Decode JWT to check expiry (basic check)
          const payload = JSON.parse(atob(token.split('.')[1]));
          const expiryTime = payload.exp * 1000; // Convert to milliseconds
          const currentTime = Date.now();
          const timeUntilExpiry = expiryTime - currentTime;
          
          if (timeUntilExpiry < 300000) { // 5 minutes warning
            setSessionWarning(`Session expires in ${Math.ceil(timeUntilExpiry / 60000)} minutes`);
          } else if (timeUntilExpiry < 0) {
            setSessionWarning("Session expired. Please login again.");
          } else {
            setSessionWarning(null);
          }
        } catch (error) {
          console.warn("Could not decode session token:", error);
        }
      }
    };
    
    checkSessionExpiry();
    const sessionInterval = setInterval(checkSessionExpiry, 60000); // Check every minute
    
    return () => {
      clearInterval(interval);
      clearInterval(sessionInterval);
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

  const handleFileUpload = async (file: File) => {
    setSelectedFile(file);
    
    try {
      // Simulate file upload - replace with actual upload logic
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Add file message to chat
      const fileMessage = `📎 Uploaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      await handleSendMessage(fileMessage);
      
      setSelectedFile(null);
    } catch (error) {
      console.error("File upload failed:", error);
    }
  };

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      
      // Navigate to login immediately for instant feedback
      router.push("/login");
      
      // Run cleanup operations in parallel (non-blocking)
      Promise.all([
        // Save chat session (non-blocking)
        saveChatSession().catch(err => 
          console.warn("Chat session save failed:", err)
        ),
        
        // Logout (non-blocking)
        logout().catch(err => 
          console.warn("Logout failed:", err)
        )
      ]).catch(error => {
        console.warn("Non-critical logout cleanup failed:", error);
      });

    } catch (error) {
      console.error("Logout failed:", error);
      setIsLoggingOut(false);
    }
  };

  // Mock reminders data
  const reminders = [
    { id: 1, text: "Follow up with Acme Corp", time: "2:00 PM", priority: "high" },
    { id: 2, text: "Review TechStart contract", time: "4:00 PM", priority: "medium" },
    { id: 3, text: "Prepare monthly report", time: "Tomorrow", priority: "low" },
  ];

  // Get last 7 messages for chat history
  const recentMessages = messages.slice(-7);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b-2 border-blue-500">
          {/* Session Warning Banner */}
          {sessionWarning && (
            <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-yellow-800">{sessionWarning}</span>
                </div>
                <button
                  onClick={() => setSessionWarning(null)}
                  className="text-yellow-600 hover:text-yellow-800"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">
                  ConsultEase AI Assistant
                </h1>
              </div>

              <div className="flex items-center space-x-4">
                {/* Redis Status Indicator */}
                <div className="flex items-center space-x-2">
                  {redisStatus === 'connected' ? (
                    <Wifi className="h-4 w-4 text-green-600" />
                  ) : redisStatus === 'disconnected' ? (
                    <WifiOff className="h-4 w-4 text-red-600" />
                  ) : (
                    <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    redisStatus === 'connected' 
                      ? 'bg-green-100 text-green-800' 
                      : redisStatus === 'disconnected'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {redisStatus === 'connected' ? 'Redis Connected' : 
                     redisStatus === 'disconnected' ? 'Redis Offline' : 'Checking...'}
                  </span>
                </div>

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
                  disabled={isLoggingOut}
                  className={`text-sm transition-colors ${
                    isLoggingOut 
                      ? "text-gray-400 cursor-not-allowed" 
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {isLoggingOut ? "Logging out..." : "Logout"}
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex h-[calc(100vh-4rem)]">
          {/* Left Panel - Reminders & Chat History */}
          <div className="w-80 bg-white border-r-2 border-blue-500 flex flex-col">
            {/* Session Info Section */}
            <div className="p-4 border-b-2 border-blue-200 bg-blue-50">
              <div className="flex items-center space-x-2 mb-3">
                <div className="h-3 w-3 bg-green-500 rounded-full"></div>
                <h3 className="text-sm font-semibold text-gray-900">Active Session</h3>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">User:</span>
                  <span className="text-gray-900 font-medium">{user?.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Role:</span>
                  <span className="text-gray-900 font-medium">{user?.role}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Redis:</span>
                  <span className={`font-medium ${
                    redisStatus === 'connected' ? 'text-green-600' : 
                    redisStatus === 'disconnected' ? 'text-red-600' : 'text-blue-600'
                  }`}>
                    {redisStatus === 'connected' ? 'Connected' : 
                     redisStatus === 'disconnected' ? 'Offline' : 'Checking...'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Messages:</span>
                  <span className="text-gray-900 font-medium">{messages.length}</span>
                </div>
              </div>
            </div>

            {/* Reminders Section */}
            <div className="flex-1 p-4 border-b-2 border-blue-200">
              <div className="flex items-center space-x-2 mb-4">
                <Clock className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">Reminders</h3>
              </div>
              <div className="space-y-3">
                {reminders.map((reminder) => (
                  <div
                    key={reminder.id}
                    className={`p-3 rounded-lg border-l-4 ${
                      reminder.priority === 'high' 
                        ? 'border-red-500 bg-red-50' 
                        : reminder.priority === 'medium'
                        ? 'border-yellow-500 bg-yellow-50'
                        : 'border-green-500 bg-green-50'
                    }`}
                  >
                    <p className="text-sm text-gray-800">{reminder.text}</p>
                    <p className="text-xs text-gray-500 mt-1">{reminder.time}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Chat History Section */}
            <div className="flex-1 p-4">
              <div className="flex items-center space-x-2 mb-4">
                <MessageSquare className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">Recent Messages</h3>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {recentMessages.length === 0 ? (
                  <p className="text-sm text-gray-500">No recent messages</p>
                ) : (
                  recentMessages.map((message, index) => (
                    <div
                      key={index}
                      className={`text-xs p-2 rounded ${
                        message.isUser 
                          ? 'bg-blue-100 text-blue-800 ml-4' 
                          : 'bg-gray-100 text-gray-800 mr-4'
                      }`}
                    >
                      <p className="truncate">
                        {message.isUser ? 'You' : message.agent}: {message.message}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col bg-gray-100">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6">
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
                <div className="space-y-6">
                  {messages.map((message) => (
                    <div key={message.id} className="flex">
                      {message.isUser ? (
                        // User message - Right side
                        <div className="flex-1 flex justify-end">
                          <div className="max-w-md bg-blue-600 text-white px-4 py-3 rounded-lg shadow-md">
                            <div className="whitespace-pre-wrap">{message.message}</div>
                            <div className="text-xs opacity-70 mt-1">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      ) : (
                        // Agent message - Left side
                        <div className="flex-1 flex justify-start">
                          <div className="max-w-md bg-white border-2 border-blue-200 px-4 py-3 rounded-lg shadow-md">
                            <div className="flex items-center space-x-2 mb-2">
                              <div className="text-xs text-gray-600">{message.agent}</div>
                              {message.success && (
                                <span className="text-green-600 text-xs">✔ success</span>
                              )}
                            </div>
                            {message.isUser ? (
                              <div className="whitespace-pre-wrap">{message.message}</div>
                            ) : (
                              <TypewriterText
                                text={message.response}
                                speed={20}
                                className="text-gray-900"
                              />
                            )}
                            <div className="text-xs text-gray-500 mt-1">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {/* Typing indicator after user messages */}
                  {messages.length > 0 && messages[messages.length - 1].isUser && isTyping && (
                    <div className="flex justify-start">
                      <div className="max-w-md bg-white border-2 border-blue-200 px-4 py-3 rounded-lg shadow-md">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-600">AI is thinking</span>
                          <div className="flex space-x-1">
                            <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"></div>
                            <div
                              className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"
                              style={{ animationDelay: "0.1s" }}
                            ></div>
                            <div
                              className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"
                              style={{ animationDelay: "0.2s" }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Chat Input Area */}
            <div className="bg-white border-t-2 border-blue-500 p-4">
              {/* File Upload Area */}
              {selectedFile && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-blue-800">{selectedFile.name}</span>
                    <span className="text-xs text-blue-600">
                      ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              {/* File Upload Button */}
              <div className="mb-3">
                <label className="inline-flex items-center px-3 py-2 border border-blue-300 rounded-md shadow-sm text-sm font-medium text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer">
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Document
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileUpload(file);
                    }}
                  />
                </label>
                <span className="ml-2 text-xs text-gray-500">
                  PDF, DOC, DOCX, JPG, PNG
                </span>
              </div>

              {/* Chat Input */}
              <ChatInput
                onSendMessage={handleSendMessage}
                isTyping={isTyping}
                placeholder="Ask about clients, contracts, time tracking, or deliverables..."
              />

              {/* Bottom Controls */}
              <div className="flex justify-between items-center mt-3">
                <button
                  onClick={clearChat}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  Clear conversation
                </button>
                <span className="text-sm text-gray-500">
                  {messages.filter(m => !m.isUser).length} AI responses
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
