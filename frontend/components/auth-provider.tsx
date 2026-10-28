"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "@/lib/api";
import { AUTH_EVENT, getToken, setToken } from "@/lib/auth-store";
import type { User } from "@/lib/types";

type AuthCtx = {
  user: User | null;
  ready: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setReady(true);
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    window.addEventListener(AUTH_EVENT, refresh);
    return () => window.removeEventListener(AUTH_EVENT, refresh);
  }, [refresh]);

  const value = useMemo(
    () => ({
      user,
      ready,
      login: async (token: string) => {
        setToken(token);
        await refresh();
      },
      logout: () => {
        setToken(null);
        setUser(null);
      },
    }),
    [user, ready, refresh]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}