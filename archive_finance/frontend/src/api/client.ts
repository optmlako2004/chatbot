// Wrapper fetch qui :
// - prefixe l'URL de l'API
// - injecte automatiquement le header Authorization (JWT) ou X-Anonymous-Id
// - parse le JSON et lève une erreur typée sur 4xx/5xx

import type {
  AuthResponse,
  ChatMessage,
  ChatResponse,
  ChatSession,
  EndSessionResponse,
  User,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "chatbot.token";
const ANON_KEY = "chatbot.anon_id";

// ----- Token / anonymous id helpers -----

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),

  getAnonId: () => {
    let id = localStorage.getItem(ANON_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(ANON_KEY, id);
    }
    return id;
  },
  clearAnonId: () => localStorage.removeItem(ANON_KEY),
};

// ----- Erreur HTTP typée -----

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
}

// ----- fetch wrapper -----

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  const token = auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    headers["X-Anonymous-Id"] = auth.getAnonId();
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 204) {
    return undefined as T;
  }

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      body.detail || body.message || `HTTP ${res.status}`;
    throw new ApiError(res.status, String(detail));
  }
  return body as T;
}

// ----- Endpoints -----

export const api = {
  // Auth
  signup: (email: string, password: string, name?: string) =>
    request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  // Stub Google : à brancher quand les clés OAuth seront dispo.
  googleStub: (data: {
    google_sub: string;
    email: string;
    name: string;
    picture?: string;
  }) =>
    request<AuthResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: () => request<User>("/auth/me"),

  // Sessions
  listSessions: () => request<ChatSession[]>("/sessions"),

  createSession: (title?: string) =>
    request<ChatSession>("/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),

  getSession: (id: string) => request<ChatSession>(`/sessions/${id}`),

  getMessages: (id: string) =>
    request<ChatMessage[]>(`/sessions/${id}/messages`),

  deleteSession: (id: string) =>
    request<void>(`/sessions/${id}`, { method: "DELETE" }),

  endSession: (id: string) =>
    request<EndSessionResponse>(`/sessions/${id}/end`, { method: "POST" }),

  sendFeedback: (id: string, rating: number, comment?: string) =>
    request<{ ok: boolean; rating: number }>(
      `/sessions/${id}/feedback`,
      { method: "POST", body: JSON.stringify({ rating, comment }) },
    ),

  // Chat
  chat: (sessionId: string, message: string) =>
    request<ChatResponse>(`/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
