/**
 * Supabase provider with React Query integration
 * Provides auth context and query client for the entire app
 */

"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/contexts/auth-context";

interface SupabaseProviderProps {
  children: ReactNode;
}

export function SupabaseProvider({ children }: SupabaseProviderProps) {
  return <AuthProvider>{children}</AuthProvider>;
}
