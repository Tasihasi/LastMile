import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { User } from "../types";
import * as api from "../api/client";

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, role: "biker" | "planner") => Promise<void>;
  logout: () => Promise<void>;
  isPlanner: boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuthProvider(): AuthContextValue {
  const hasToken = !!localStorage.getItem("auth-token");
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(hasToken);

  // On mount, validate existing token
  useEffect(() => {
    if (!hasToken) return;
    api
      .getMe()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem("auth-token");
      })
      .finally(() => setLoading(false));
  }, [hasToken]);

  const login = useCallback(
    async (username: string, role: "biker" | "planner") => {
      const res = await api.login(username, role);
      localStorage.setItem("auth-token", res.token);
      setUser(res.user);
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // ignore errors
    }
    localStorage.removeItem("auth-token");
    setUser(null);
  }, []);

  const isPlanner = user?.role === "planner";

  return { user, loading, login, logout, isPlanner };
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
