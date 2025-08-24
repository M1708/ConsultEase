import { User } from "@/types/user";
import { SendMessageRequest, AgentCapabilities, ChatResponse } from "@/types/chat";
import { supabase } from "./supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  // private async getAuthHeaders() {
  //   const {
  //     data: { session },
  //   } = await supabase.auth.getSession();
  //   return {
  //     "Content-Type": "application/json",
  //     ...(session?.access_token && {
  //       Authorization: `Bearer ${session.access_token}`,
  //     }),
  //   };
  // }
  private async getAuthHeaders() {
    const token = localStorage.getItem("supabase_token");
    return {
      "Content-Type": "application/json",
      ...(token && {
        Authorization: `Bearer ${token}`,
      }),
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "Request failed" }));
      throw new Error(errorData.detail || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  // Auth API
  auth = {
    getUserProfile: async (authUserId: string): Promise<User> => {
      return this.request<User>(`/api/auth/profile/${authUserId}`);
    },

    updateLastLogin: async (userId: string): Promise<void> => {
      return this.request(`/api/auth/users/${userId}/last-login`, {
        method: "PATCH",
      });
    },
  };

  // Chat API
  chat = {
    sendMessage: async (request: SendMessageRequest): Promise<ChatResponse> => {
      return this.request<ChatResponse>("/api/chat/message", {
        method: "POST",
        body: JSON.stringify(request),
      });
    },

    getAgents: async (): Promise<AgentCapabilities> => {
      return this.request("/api/chat/agents");
    },

    getWorkflowStatus: async (workflowId: string) => {
      return this.request("/api/chat/workflow/status", {
        method: "POST",
        body: JSON.stringify({ workflow_id: workflowId }),
      });
    },

    healthCheck: async () => {
      return this.request("/api/chat/health");
    },
  };
}

const apiClient = new ApiClient();

// Export individual API modules for easier imports
export const authApi = apiClient.auth;
export const chatApi = apiClient.chat;
export default apiClient;
