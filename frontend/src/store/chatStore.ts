import { create } from "zustand";
import { ChatMessage, ChatState, SendMessageRequest } from "@/types/chat";
import { chatApi } from "@/lib/api";
//import { useAuthStore } from './authStore'
import { useAuthStore } from "@/store/authStore";

interface ChatStore extends ChatState {
  sendMessage: (message: string, displayMessage?: string) => Promise<void>;
  clearMessages: () => void;
  setTyping: (typing: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  clearError: () => void;
  loadChatSession: () => Promise<void>;
  saveChatSession: () => Promise<void>;
}

const saveChatToRedis = async (
  messages: ChatMessage[],
  sessionId: string,
  userId: string
) => {
  try {
    const token = localStorage.getItem("supabase_token");
    if (!token) return;

    await fetch(
      `${
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      }/api/chat/session`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          chat_data: {
            messages,
            lastActivity: new Date().toISOString(),
          },
        }),
      }
    );
    console.log("Chat saved to Redis");
  } catch (error) {
    console.error("Failed to save chat:", error);
  }
};

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isTyping: false,
  error: null,
  sessionId: `session_${Date.now()}`,

  sendMessage: async (messageText: string, displayMessage?: string) => {
    const { user } = useAuthStore.getState();
    const state = get();

    if (!user) {
      set({ error: "User not authenticated" });
      return;
    }

    try {
      set({ isTyping: true, error: null });

      // Add user message to chat
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}`,
        message: displayMessage || messageText,
        response: "",
        agent: "User",
        success: true,
        timestamp: new Date().toISOString(),
        session_id: state.sessionId,
        isUser: true,
        data: {},
      };

      set((state) => ({
        messages: [...state.messages, userMessage],
      }));

      // Send to backend
      const request: SendMessageRequest = {
        message: messageText,
        user_id: user.user_id,
        session_id: state.sessionId,
        context: {
          user_role: user.role,
          user_name: user.full_name,
          user_first_name: user.first_name || user.full_name?.split(' ')[0] || 'User',
          user_last_name: user.last_name || user.full_name?.split(' ')[1] || '',
          conversation_history: state.messages.map(msg => ({
            role: msg.isUser ? 'user' : 'assistant',
            content: msg.isUser ? msg.message : msg.response,
            timestamp: msg.timestamp
          })),
          current_session: state.sessionId,
          previous_context: state.messages.length > 0 ? {
            last_user_message: state.messages[state.messages.length - 1]?.message || '',
            last_agent_response: state.messages[state.messages.length - 1]?.response || '',
            conversation_length: state.messages.length
          } : null
        },
      };

      const response = await chatApi.sendMessage(request);

      // Check if the request was successful
      if (!response.success) {
        throw new Error(response.response || response.error || 'Request failed');
      }

      // Add agent response to chat
      const agentMessage: ChatMessage = {
        id: `agent_${Date.now()}`,
        message: messageText,
        response: response.response,
        agent: response.agent,
        success: response.success,
        timestamp: response.timestamp,
        session_id: response.session_id,
        workflow_id: response.workflow_id,
        data: response.data,
        isUser: false,
      };

      set((state) => ({
        messages: [...state.messages, agentMessage],
        isTyping: false,
      }));

      const currentMessages = get().messages;
      await saveChatToRedis(currentMessages, state.sessionId, user.user_id);
    } catch (error) {
      console.error("Failed to send message:", error);
      set({
        isTyping: false,
        error:
          error instanceof Error ? error.message : "Failed to send message",
      });
    }
  },

  clearMessages: () =>
    set({
      messages: [],
      sessionId: `session_${Date.now()}`,
      error: null,
    }),

  setTyping: (typing: boolean) => set({ isTyping: typing }),

  addMessage: (message: ChatMessage) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setMessages: (messages) =>
    set((state) => ({
      messages: typeof messages === 'function' ? messages(state.messages) : messages,
    })),

  clearError: () => set({ error: null }),

  loadChatSession: async () => {
    const { user } = useAuthStore.getState();
    const { sessionId } = get();

    if (!user || !sessionId) return;

    try {
      const token = localStorage.getItem("supabase_token");
      if (!token) return;

      const response = await fetch(
        `${
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        }/api/chat/session/${sessionId}?user_id=${user.user_id}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
          console.log("Restored", data.messages.length, "previous messages");
          set({ 
            messages: data.messages,
            sessionId: data.session_id || sessionId // Ensure we keep the same session ID
          });
        }
      }
    } catch (error) {
      console.error("Failed to load chat session:", error);
    }
  },

  saveChatSession: async () => {
    const { user } = useAuthStore.getState();
    const { messages, sessionId } = get();

    if (!user || !sessionId || messages.length === 0) return;

    try {
      const token = localStorage.getItem("supabase_token");
      if (!token) return;

      await fetch(
        `${
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        }/api/chat/session`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            user_id: user.user_id,
            chat_data: {
              messages,
              lastActivity: new Date().toISOString(),
            },
          }),
        }
      );
      console.log("Chat saved to Redis");
    } catch (error) {
      console.error("Failed to save chat:", error);
    }
  },
}));
