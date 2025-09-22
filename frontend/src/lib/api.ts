import { User } from "@/types/user";
import {
  SendMessageRequest,
  AgentCapabilities,
  ChatResponse,
} from "@/types/chat";
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

  private async sendFastGreeting(
    request: SendMessageRequest
  ): Promise<ChatResponse> {
    // Use minimal headers for ultra-fast greeting (no auth to avoid middleware)
    const response = await fetch(`${API_BASE_URL}/api/chat/greeting`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      // Fallback to regular message endpoint if fast greeting fails
      console.log("Fast greeting failed, falling back to regular endpoint");
      return this.request<ChatResponse>("/api/chat/message", {
        method: "POST",
        body: JSON.stringify(request),
      });
    }

    return response.json();
  }

  private async sendFastClients(
    request: SendMessageRequest
  ): Promise<ChatResponse> {
    // Use authenticated request for client data
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/chat/clients`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      // Fallback to regular message endpoint if fast clients fails
      console.log("Fast clients failed, falling back to regular endpoint");
      return this.request<ChatResponse>("/api/chat/message", {
        method: "POST",
        body: JSON.stringify(request),
      });
    }

    return response.json();
  }

  // Chat API
  chat = {
    sendMessage: async (request: SendMessageRequest): Promise<ChatResponse> => {
      // Check if it's a greeting message for ultra-fast response
      const message = request.message.toLowerCase().trim();
      console.log(`🔍 FRONTEND: Checking message: "${message}"`);

      const greetings = ["hi", "hello", "hey", "hola", "howdy", "greetings"];
      const greetingPhrases = [
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
      ];

      const isSimpleGreeting = greetings.includes(message);
      const isPhraseGreeting = greetingPhrases.some((phrase) =>
        message.includes(phrase)
      );
      const isGreeting = isSimpleGreeting || isPhraseGreeting;

      console.log(
        `🔍 FRONTEND: Simple: ${isSimpleGreeting}, Phrase: ${isPhraseGreeting}, Final: ${isGreeting}`
      );

      if (isGreeting) {
        console.log("🚀 FRONTEND: Using fast greeting endpoint!");
        const startTime = performance.now();
        try {
          const result = await this.sendFastGreeting(request);
          const endTime = performance.now();
          console.log(
            `⚡ FRONTEND: Fast greeting completed in ${endTime - startTime}ms`
          );
          return result;
        } catch (error) {
          const endTime = performance.now();
          console.log(
            `❌ FRONTEND: Fast greeting failed after ${endTime - startTime}ms:`,
            error
          );
          throw error;
        }
      }

      // Check if it's a client listing query for ultra-fast response
      const clientQueries = [
        "show all clients",
        "list all clients",
        "get all clients",
        "all clients",
        "show clients",
        "list clients",
        "get clients",
        "clients list",
        "what clients do we have",
        "who are our clients",
        "client list",
      ];

      // Check for complex queries that should go through normal routing
      const complexQueries = [
        "clients with contracts", "clients and contracts", "clients along with contracts",
        "show clients with their contracts", "list clients and their contracts",
        "clients with their contracts", "all clients with their contracts",
        "show me all clients with their contracts", "show all clients with contracts",
        // Billing-related queries that should go through contract_agent
        "billing", "billing date", "billing prompt", "upcoming billing",
        "next billing", "billing frequency", "contracts with billing",
        // Amount filtering queries that should go through contract_agent
        "amount more than", "original amount more than", "amount greater than",
        "original amount greater than", "more than $", "greater than $",
        "contracts for all clients with", "contracts with amount"
      ];

      const isComplexQuery = complexQueries.some((query) =>
        message.toLowerCase().includes(query)
      );
      const isClientQuery = clientQueries.some((query) =>
        message.includes(query)
      ) && !isComplexQuery;

      if (isClientQuery) {
        console.log("🚀 FRONTEND: Using fast clients endpoint!");
        const startTime = performance.now();
        try {
          const result = await this.sendFastClients(request);
          const endTime = performance.now();
          console.log(
            `⚡ FRONTEND: Fast clients completed in ${endTime - startTime}ms`
          );
          return result;
        } catch (error) {
          const endTime = performance.now();
          console.log(
            `❌ FRONTEND: Fast clients failed after ${endTime - startTime}ms:`,
            error
          );
          throw error;
        }
      }

      console.log("🔄 FRONTEND: Using regular endpoint");
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
