// Contexte React pour l'utilisateur connecté.
// Au montage, tente de récupérer /auth/me (avec le JWT en localStorage si présent,
// ou en mode anonyme via X-Anonymous-Id). Permet login / signup / logout.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api, auth as authStorage } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    authStorage.setToken(res.token);
    setUser(res.user);
  }, []);

  const signup = useCallback(
    async (email: string, password: string, name?: string) => {
      const res = await api.signup(email, password, name);
      authStorage.setToken(res.token);
      setUser(res.user);
    },
    [],
  );

  const logout = useCallback(() => {
    authStorage.clearToken();
    authStorage.clearAnonId();
    setUser(null);
    // refresh() recréera un user anonyme à la prochaine page
    refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
