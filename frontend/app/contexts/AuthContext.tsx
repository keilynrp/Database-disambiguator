"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/api";

interface User {
  id: number;
  username: string;
  role: string;
  email: string | null;
  is_active: boolean;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  // Hydrate from localStorage on first render (client-only)
  useEffect(() => {
    const stored = localStorage.getItem("ukip_token");
    if (stored) {
      setToken(stored);
      fetch(`${API_BASE}/users/me`, {
        headers: { Authorization: `Bearer ${stored}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => { if (data) setUser(data); })
        .catch(() => {});
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${API_BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!res.ok) {
      throw new Error("Invalid credentials");
    }
    const data = await res.json();
    localStorage.setItem("ukip_token", data.access_token);
    setToken(data.access_token);

    // Fetch user profile after login
    const meRes = await fetch(`${API_BASE}/users/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    if (meRes.ok) setUser(await meRes.json());
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("ukip_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
