// Types qui matchent les schémas Pydantic du backend (api.py).

export interface User {
  id: string;
  email: string | null;
  name: string | null;
  picture: string | null;
  is_anonymous: boolean;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface ChatSession {
  id: string;
  title: string;
  status: "active" | "ended";
  created_at: string;
  ended_at: string | null;
  rating: number | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_used: string | null;
  created_at: string;
}

export interface ChatResponse {
  answer: string;
  tools_used: string[];
  message_id: string;
}

export interface EndSessionResponse {
  farewell: string;
  session_id: string;
}
