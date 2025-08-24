interface SessionData {
  sessionId: string;
  userId: string;
  email: string;
  role: string;
  createdAt: string;
  lastAccessed: string;
}

interface ChatSessionData {
  messages: unknown[];
  sessionId: string;
  lastActivity: string;
}

class RedisSessionManager {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }

  async getSession(token: string): Promise<SessionData | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/session`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) return null;
      const userData = await response.json();

      return {
        sessionId: "current-session", // We'll get actual session ID later
        userId: userData.user_id,
        email: userData.email,
        role: userData.role,
        createdAt: userData.created_at,
        lastAccessed: new Date().toISOString(),
      };
    } catch (error) {
      console.error("Failed to get session:", error);
      return null;
    }
  }

  async invalidateSession(token: string): Promise<boolean> {
    try {
      // Use AbortController for timeout to prevent hanging requests
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
      
      const response = await fetch(`${this.baseUrl}/api/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.warn("Session invalidation timed out, continuing with logout");
      } else {
        console.error("Failed to invalidate session:", error);
      }
      return false;
    }
  }
}

export const redisSessionManager = new RedisSessionManager();
export type { SessionData, ChatSessionData };
