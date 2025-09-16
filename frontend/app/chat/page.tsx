"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { useChatSession } from "@/hooks/useChatSession";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { TypewriterText } from "@/components/chat/TypewriterText";
import { useAuthStore } from "@/store/authStore";
import { ChatMessage } from "@/types/chat";
import { Upload, Clock, FileText, X, User, Bot, Send } from "lucide-react";

export default function ChatPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const {
    messages,
    isTyping,
    sendMessage,
    clearChat,
    sessionId,
    setTyping,
    setMessages,
  } = useChat();
  const { loadChatSession, saveChatSession } = useChatSession();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [redisStatus, setRedisStatus] = useState<
    "connected" | "disconnected" | "checking"
  >("checking");
  const [sessionWarning, setSessionWarning] = useState<string | null>(null);
  const [leftPanelWidth, setLeftPanelWidth] = useState(320);
  const [chatAreaWidth, setChatAreaWidth] = useState(() => {
    // Initialize with responsive width based on browser window size
    if (typeof window !== "undefined") {
      return Math.max(400, window.innerWidth - 370); // 320px left panel + 50px margins
    }
    return 800; // Fallback for SSR
  });
  const [isDragging, setIsDragging] = useState(false);
  //const [isDraggingChat, setIsDraggingChat] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load chat session on mount (non-blocking)
  useEffect(() => {
    // Load session in background without blocking UI
    setTimeout(() => {
      loadChatSession();
    }, 100); // Small delay to let UI render first
  }, [loadChatSession]);

  // Handle resizing
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  };

  /*const handleChatMouseDown = (e: React.MouseEvent) => {
    setIsDraggingChat(true);
    e.preventDefault();
  };*/

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      const newWidth = Math.min(Math.max(e.clientX, 250), 500);
      setLeftPanelWidth(newWidth);

      // Adjust chat area width when left panel is resized to prevent overflow
      //const availableSpace = window.innerWidth - newWidth - 50;
      //const newChatWidth = Math.max(400, availableSpace);
      //setChatAreaWidth(newChatWidth);
    }
    //if (isDraggingChat) {
    // Calculate available space after left panel and margins
    //const availableSpace = window.innerWidth - leftPanelWidth - 50; // 50px for margins and resize handles
    //const newWidth = Math.min(Math.max(e.clientX - leftPanelWidth, 400), availableSpace);
    //setChatAreaWidth(newWidth);
    //}
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    //setIsDraggingChat(false);
  };

  useEffect(
    () => {
      //if (isDragging || isDraggingChat) {
      if (isDragging) {
        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
      }
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }, //[isDragging, isDraggingChat, leftPanelWidth]);
    [isDragging, leftPanelWidth]
  );

  // Handle window resize to adjust chat area width
  useEffect(() => {
    const handleWindowResize = () => {
      const availableSpace = window.innerWidth - leftPanelWidth - 50;
      const newWidth = Math.max(400, availableSpace);
      setChatAreaWidth(newWidth);
    };

    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, [leftPanelWidth]);

  useEffect(() => {
    const authState = useAuthStore.getState();
    console.log("Session ID:", authState.sessionId);

    // Check Redis connection status
    const checkRedisStatus = async () => {
      try {
        const token = localStorage.getItem("supabase_token");
        if (token) {
          // Simple ping to check if Redis is accessible
          const response = await fetch(
            `${
              process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
            }/api/chat/health`
          );
          if (response.ok) {
            setRedisStatus("connected");
          } else {
            setRedisStatus("disconnected");
          }
        } else {
          setRedisStatus("disconnected");
        }
      } catch (error) {
        console.warn("Redis status check failed:", error);
        setRedisStatus("disconnected");
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
          const payload = JSON.parse(atob(token.split(".")[1]));
          const expiryTime = payload.exp * 1000; // Convert to milliseconds
          const currentTime = Date.now();
          const timeUntilExpiry = expiryTime - currentTime;

          if (timeUntilExpiry < 300000) {
            // 5 minutes warning
            setSessionWarning(
              `Session expires in ${Math.ceil(timeUntilExpiry / 60000)} minutes`
            );
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
  }, [messages, isTyping]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("🚀 Frontend: handleSendMessage called", {
      selectedFile,
      inputMessage,
      isTyping,
    });
    if ((!selectedFile && !inputMessage) || isTyping) return;

    // TODO: INPUT CLEARING FIX - Clear input immediately when user hits enter
    const messageToSend = inputMessage.trim();
    const fileToSend = selectedFile;

    // Clear input immediately
    setInputMessage("");
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    console.log("🧹 Frontend: Input cleared immediately when user hit enter");

    try {
      if (fileToSend && messageToSend) {
        console.log("🚀 Frontend: Calling sendMessageWithFile", {
          selectedFile: fileToSend.name,
          inputMessage: messageToSend,
        });
        // NEW: Send file with message to agentic endpoint
        await sendMessageWithFile(fileToSend, messageToSend);
      } else if (messageToSend) {
        // Handle text-only message
        if (["hi", "hello", "hey"].includes(messageToSend.toLowerCase())) {
          await sendMessage(
            `${messageToSend} my name is ${user?.first_name}`,
            messageToSend
          );
        } else {
          await sendMessage(messageToSend);
        }
      }
      // Auto-save after sending message
      await saveChatSession();
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  // NEW: Function for sending file with message to agentic endpoint
  const sendMessageWithFile = async (file: File, message: string) => {
    console.log("🚀 Frontend: sendMessageWithFile called", {
      file: file.name,
      message,
    });
    try {
      setTyping(true);

      // Add user message to chat immediately
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}`,
        message: `📎 ${file.name} - ${message}`,
        response: "",
        agent: "User",
        success: true,
        timestamp: new Date().toISOString(),
        session_id: sessionId,
        isUser: true,
        data: {},
      };

      setMessages((prev) => [...prev, userMessage]);

      // Send to new agentic endpoint
      const formData = new FormData();
      formData.append("message", message);
      formData.append("file", file);
      formData.append("session_id", sessionId);

      const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("supabase_token");
      const response = await fetch(
        `${API_BASE_URL}/api/chat/message-with-file`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Backend error response:", errorText);
        throw new Error(
          `Failed to send message with file: ${response.status} - ${errorText}`
        );
      }

      const result = await response.json();

      // Check if the request was successful
      if (!result.success) {
        throw new Error(result.response || result.error || "Request failed");
      }

      // Add agent response to chat
      const agentMessage: ChatMessage = {
        id: `agent_${Date.now()}`,
        message: message,
        response: result.response,
        agent: result.agent,
        success: result.success,
        timestamp: result.timestamp,
        session_id: result.session_id,
        workflow_id: result.workflow_id,
        data: result.data,
        isUser: false,
      };

      setMessages((prev) => [...prev, agentMessage]);
      setTyping(false);
    } catch (error) {
      console.error("Failed to send message with file:", error);
      setTyping(false);
      // Add error message to chat
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        message: `📎 ${file.name} - ${message}`,
        response: `❌ Error: ${
          error instanceof Error ? error.message : "Failed to process file"
        }`,
        agent: "Error",
        success: false,
        timestamp: new Date().toISOString(),
        session_id: sessionId,
        isUser: false,
        data: {},
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // NEW: Handle file selection without immediate upload
  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    // Don't upload immediately - wait for user message
  };

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);

      // Navigate to login immediately for instant feedback
      router.push("/login");

      // Run cleanup operations in parallel (non-blocking)
      Promise.all([
        // Save chat session (non-blocking)
        saveChatSession().catch((err) =>
          console.warn("Chat session save failed:", err)
        ),

        // Logout (non-blocking)
        logout().catch((err) => console.warn("Logout failed:", err)),
      ]).catch((error) => {
        console.warn("Non-critical logout cleanup failed:", error);
      });
    } catch (error) {
      console.error("Logout failed:", error);
      setIsLoggingOut(false);
    }
  };

  // Mock reminders data (you can replace this with real data from your backend)
  const reminders = [
    {
      id: 1,
      text: "Follow up with Acme Corp",
      time: "2:00 PM",
      priority: "high",
    },
    {
      id: 2,
      text: "Review TechStart contract",
      time: "4:00 PM",
      priority: "medium",
    },
    {
      id: 3,
      text: "Prepare monthly report",
      time: "Tomorrow",
      priority: "low",
    },
  ];

  return (
    <ProtectedRoute>
      <div className="h-screen bg-gray-100 overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm border-b-2 border-blue-400 flex-shrink-0">
          {/* Session Warning Banner */}
          {sessionWarning && (
            <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-yellow-800">
                    {sessionWarning}
                  </span>
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

          <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1
                  className="text-3xl font-bold text-gray-900"
                  style={{ fontFamily: "Playfair Display, Georgia, serif" }}
                >
                  Effiscale Consulting
                </h1>
              </div>
              <div className="flex items-center">
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className={`px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 hover:shadow-md rounded-lg transition-all duration-200 ${
                    isLoggingOut ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  style={{ fontFamily: "Arial, sans-serif" }}
                >
                  {isLoggingOut ? "Logging out..." : "Logout"}
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
          {/* Left Panel - Resizable */}
          <div
            className="bg-white border-r-2 border-blue-400 flex flex-col flex-shrink-0 overflow-hidden"
            style={{
              width: `${leftPanelWidth}px`,
              minWidth: "250px",
              maxWidth: "500px",
            }}
          >
            {/* User Name Section */}
            <div className="p-4 bg-blue-50 flex-shrink-0 flex items-center justify-center min-h-[60px]">
              <div className="flex items-center space-x-2">
                <div className="h-3 w-3 bg-green-500 rounded-full"></div>
                <h3
                  className="text-lg font-bold text-gray-900 truncate text-center"
                  style={{ fontFamily: "Arial, sans-serif" }}
                >
                  {user?.full_name ||
                    `${user?.first_name || ""} ${
                      user?.last_name || ""
                    }`.trim() ||
                    user?.email ||
                    "User"}
                </h3>
              </div>
            </div>

            <div className="h-8 flex-shrink-0"></div>

            {/* Reminders Section */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="flex items-center space-x-2 mb-4">
                <Clock className="h-5 w-5 text-blue-600 flex-shrink-0" />
                <h3
                  className="text-lg font-semibold text-gray-900"
                  style={{ fontFamily: "Arial, sans-serif" }}
                >
                  Reminders
                </h3>
              </div>
              <div className="space-y-3">
                {reminders.map((reminder) => (
                  <div
                    key={reminder.id}
                    className={`p-3 rounded-lg border-l-4 ${
                      reminder.priority === "high"
                        ? "border-red-500 bg-red-50"
                        : reminder.priority === "medium"
                        ? "border-yellow-500 bg-yellow-50"
                        : "border-green-500 bg-green-50"
                    }`}
                  >
                    <p
                      className="text-sm text-gray-800"
                      style={{ fontFamily: "Arial, sans-serif" }}
                    >
                      {reminder.text}
                    </p>
                    <p
                      className="text-xs text-gray-500 mt-1"
                      style={{ fontFamily: "Arial, sans-serif" }}
                    >
                      {reminder.time}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Resize Handle for Left Panel - Enhanced */}
          <div
            className="w-2 bg-blue-400 cursor-ew-resize hover:bg-blue-500 hover:w-3 transition-all duration-200 flex-shrink-0 relative z-10"
            onMouseDown={handleMouseDown}
            style={{
              boxShadow: "0 0 10px rgba(59, 130, 246, 0.3)",
              minHeight: "100%",
            }}
          >
            {/* Visual indicator for resize handle */}
            <div className="absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-0.5 bg-white opacity-60"></div>
          </div>

          {/* Main Chat Area - Resizable only from the left panel */}
          <div
            //className="flex flex-col bg-white border-2 border-blue-400 rounded-lg m-2 overflow-hidden flex-shrink-0 relative"
            className="flex flex-col bg-white border-l-2 border-t-2 border-b-2 border-blue-400 border-r-[4px] m-2 overflow-hidden flex-1"
            style={{
              width: `${chatAreaWidth}px`,
              minWidth: "400px",
            }}
          >
            {/* Messages Area */}
            <div
              className="flex-1 overflow-y-auto px-6 py-4"
              style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
            >
              <style>{`
                .chat-messages::-webkit-scrollbar {
                  display: none;
                }
              `}</style>
              <div className="max-w-4xl mx-auto space-y-6 chat-messages">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-500 mt-4">
                    <h3
                      className="text-lg font-semibold mb-2 text-gray-700"
                      style={{ fontFamily: "Playfair Display, Georgia, serif" }}
                    >
                      Welcome to Effiscale Consulting
                    </h3>
                    <p
                      className="text-gray-600"
                      style={{ fontFamily: "Arial, sans-serif" }}
                    >
                      Ask me anything about your clients, contracts, time
                      tracking, deliverables, or employees.
                    </p>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className="flex items-start space-x-3">
                      {msg.isUser ? (
                        <>
                          <div className="flex-1"></div>
                          <div className="max-w-md bg-blue-600 text-white px-4 py-3 rounded-lg shadow-md">
                            <div
                              className="whitespace-pre-wrap text-base"
                              style={{ fontFamily: "Arial, sans-serif" }}
                            >
                              {msg.message}
                            </div>
                            <div
                              className="text-xs opacity-70 mt-1"
                              style={{ fontFamily: "Arial, sans-serif" }}
                            >
                              {new Date(msg.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                          <div className="h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                            <User className="h-4 w-4 text-gray-600" />
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <Bot className="h-4 w-4 text-blue-600" />
                          </div>
                          <div className="max-w-md bg-white px-4 py-3 rounded-lg shadow-md">
                            <div className="mb-2">
                              <div
                                className="text-xs font-bold text-gray-600"
                                style={{ fontFamily: "Arial, sans-serif" }}
                              >
                                <strong>{msg.agent}</strong>
                              </div>
                            </div>
                            <TypewriterText
                              text={msg.response}
                              className="text-gray-900 text-sm"
                              style={{ fontFamily: "Arial, sans-serif" }}
                            />
                            <div
                              className="text-xs text-gray-500 mt-1"
                              style={{ fontFamily: "Arial, sans-serif" }}
                            >
                              {new Date(msg.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                          <div className="flex-1"></div>
                        </>
                      )}
                    </div>
                  ))
                )}

                {/* Typing indicator */}
                {isTyping && (
                  <div className="flex items-start space-x-3">
                    <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="max-w-md bg-white px-4 py-3 rounded-lg shadow-md">
                      <div className="flex items-center space-x-2">
                        <span
                          className="text-base text-gray-600"
                          style={{ fontFamily: "Arial, sans-serif" }}
                        >
                          <strong>Milo</strong> is thinking
                        </span>
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
                    <div className="flex-1"></div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Chat Input Area */}
            <div className="bg-white border-t-2 border-blue-400 p-4 flex-shrink-0">
              <div className="max-w-4xl mx-auto">
                {/* Selected File Display - Moved above input area */}
                {selectedFile && (
                  <div className="mb-3 flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-sm text-blue-600 flex items-center gap-2">
                      📎 {selectedFile.name} (
                      {(selectedFile.size / 1024).toFixed(1)} KB)
                    </span>
                    <button
                      onClick={() => {
                        setSelectedFile(null);
                        // Clear the file input to allow selecting the same file again
                        if (fileInputRef.current) {
                          fileInputRef.current.value = "";
                        }
                      }}
                      className="text-red-500 hover:text-red-700 text-sm font-medium px-2 py-1 rounded hover:bg-red-50"
                    >
                      ✕ Remove
                    </button>
                  </div>
                )}

                {/* Chat Input with File Upload */}
                <form
                  onSubmit={handleSendMessage}
                  className="flex items-end space-x-3"
                >
                  {/* File Upload Button */}
                  <div className="flex-shrink-0">
                    <label className="inline-flex items-center justify-center w-12 h-12 border-2 border-blue-600 rounded-full shadow-lg text-blue-600 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 cursor-pointer transition-all duration-200 transform hover:scale-110">
                      <Upload className="h-6 w-6" />
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileSelect(file);
                        }}
                      />
                    </label>
                  </div>

                  {/* Chat Input */}
                  <div className="flex-1 flex space-x-3">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage(e);
                        }
                      }}
                      placeholder="Ask about clients, contracts, time tracking, deliverables, or employees..."
                      disabled={isTyping}
                      className="flex-1 resize-none border-2 border-blue-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 text-gray-900 placeholder-gray-500 text-lg"
                      style={{
                        fontFamily: "Arial, sans-serif",
                        fontSize: "18px",
                      }}
                      rows={2}
                    />
                    <button
                      type="submit"
                      disabled={
                        isTyping || (!inputMessage?.trim() && !selectedFile)
                      }
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center space-x-2"
                      style={{ fontFamily: "Arial, sans-serif" }}
                    >
                      {isTyping ? (
                        <div className="flex items-center space-x-1">
                          <span>Milo is thinking</span>
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
                            <div
                              className="w-2 h-2 bg-white rounded-full animate-bounce"
                              style={{ animationDelay: "0.1s" }}
                            ></div>
                            <div
                              className="w-2 h-2 bg-white rounded-full animate-bounce"
                              style={{ animationDelay: "0.2s" }}
                            ></div>
                          </div>
                        </div>
                      ) : (
                        <>
                          <Send className="h-5 w-5" />
                          <span>Send</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {/* Bottom Controls */}
                <div className="flex justify-end items-center mt-3">
                  <button
                    onClick={clearChat}
                    className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1 rounded-md hover:bg-gray-100 transition-colors"
                    style={{ fontFamily: "Arial, sans-serif" }}
                  >
                    Clear conversation
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Resize Handle for Chat Area - Enhanced */}
          {/* <div
            className="w-2 bg-blue-400 cursor-ew-resize hover:bg-blue-500 hover:w-3 transition-all duration-200 flex-shrink-0 relative z-10"
            onMouseDown={handleChatMouseDown}
            style={{
              boxShadow: "0 0 10px rgba(59, 130, 246, 0.3)",
              minHeight: "100%",
            }}
          > */}
          {/* Visual indicator for resize handle */}
          {/* <div className="absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-0.5 bg-white opacity-60"></div>
          </div> */}
        </div>
      </div>
    </ProtectedRoute>
  );
}
