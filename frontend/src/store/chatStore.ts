import { create } from 'zustand'
import { ChatMessage, ChatState, SendMessageRequest } from '@/types/chat'
import { chatApi } from '@/lib/api'
import { useAuthStore } from './authStore'

interface ChatStore extends ChatState {
  sendMessage: (message: string) => Promise<void>
  clearMessages: () => void
  setTyping: (typing: boolean) => void
  addMessage: (message: ChatMessage) => void
  clearError: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isTyping: false,
  error: null,
  sessionId: `session_${Date.now()}`,

  sendMessage: async (messageText: string) => {
    const { user } = useAuthStore.getState()
    const state = get()

    if (!user) {
      set({ error: 'User not authenticated' })
      return
    }

    try {
      set({ isTyping: true, error: null })

      // Add user message to chat
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}`,
        message: messageText,
        response: '',
        agent: 'User',
        success: true,
        timestamp: new Date().toISOString(),
        session_id: state.sessionId,
        isUser: true,
        data: {}
      }

      set(state => ({
        messages: [...state.messages, userMessage]
      }))

      // Send to backend
      const request: SendMessageRequest = {
        message: messageText,
        user_id: user.user_id,
        session_id: state.sessionId,
        context: {
          user_role: user.role,
          user_name: user.full_name
        }
      }

      const response = await chatApi.sendMessage(request)

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
        isUser: false
      }

      set(state => ({
        messages: [...state.messages, agentMessage],
        isTyping: false
      }))

    } catch (error) {
      console.error('Failed to send message:', error)
      set({
        isTyping: false,
        error: error instanceof Error ? error.message : 'Failed to send message'
      })
    }
  },

  clearMessages: () => set({ 
    messages: [], 
    sessionId: `session_${Date.now()}` 
  }),

  setTyping: (typing: boolean) => set({ isTyping: typing }),

  addMessage: (message: ChatMessage) => set(state => ({
    messages: [...state.messages, message]
  })),

  clearError: () => set({ error: null })
}))