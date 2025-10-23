/**
 * Supabase provider with React Query integration
 * Provides auth context and query client for the entire app
 */

"use client";

import { useEffect } from "react";
import { AuthProvider } from "@/contexts/auth-context";

interface SupabaseProviderProps {
  children: React.ReactNode;
  initialSession?: any;
}

export function SupabaseProvider({ children, initialSession }: SupabaseProviderProps) {
  // Optionally perform any one-time client init side-effects here
  useEffect(() => {
    // noop placeholder; hooks that call useSupabase() will initialize the client
  }, []);

  return <AuthProvider>{children}</AuthProvider>;
}
