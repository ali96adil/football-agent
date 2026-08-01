"use client";

import { createContext, useContext } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type Role = "admin" | "operator" | "viewer";
export interface CurrentUser { id: string; username: string; display_name: string; role: Role }

const AuthContext = createContext<{
  user: CurrentUser | null; loading: boolean; logout: () => Promise<void>;
}>({ user: null, loading: true, logout: async () => undefined });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["auth", "me"], queryFn: () => api<CurrentUser>("/api/v1/auth/me"),
    retry: false, staleTime: 60_000,
  });
  const logout = async () => {
    await api("/api/v1/auth/logout", { method: "POST" });
    queryClient.setQueryData(["auth", "me"], null);
    window.location.href = "/login";
  };
  return <AuthContext.Provider value={{ user: query.data ?? null, loading: query.isLoading, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
export const canOperate = (role?: Role) => role === "operator" || role === "admin";
export const canAdmin = (role?: Role) => role === "admin";
