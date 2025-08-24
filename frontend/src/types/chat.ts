export interface ChatMessage {
  id: string;
  message: string;
  response: string;
  agent: string;
  success: boolean;
  timestamp: string;
  session_id: string;
  workflow_id?: string;
  data?: Record<string, unknown>;
  isUser: boolean;
}

export interface ChatState {
  messages: ChatMessage[];
  isTyping: boolean;
  error: string | null;
  sessionId: string;
}

export interface SendMessageRequest {
  message: string;
  user_id?: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  agent: string;
  success: boolean;
  timestamp: string;
  session_id: string;
  workflow_id?: string;
  data?: Record<string, unknown>;
}

export interface AgentCapabilities {
  available_agents: Record<
    string,
    {
      name: string;
      description: string;
      capabilities: string[];
      tools: string[];
    }
  >;
  available_workflows: string[];
  active_workflows: number;
}
