/**
 * Supabase provider with React Query integration
 * Provides auth context and query client for the entire app
 */

"use client";

import { AuthProvider } from "@/contexts/auth-context";
import { createClient } from "@/lib/supabase/client";
import { SessionContextProvider } from "@supabase/auth-helpers-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

interface SupabaseProviderProps {
  children: React.ReactNode;
  initialSession?: any;
}

export function SupabaseProvider({ children, initialSession }: SupabaseProviderProps) {
  // Create Supabase client
  const [supabase] = useState(() => createClient());

  // Create Query Client with optimized defaults
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Don't refetch on window focus for better UX
            refetchOnWindowFocus: false,
            // Retry failed requests 3 times
            retry: 3,
            // Cache data for 5 minutes by default
            staleTime: 5 * 60 * 1000,
            // Keep data in cache for 10 minutes
            gcTime: 10 * 60 * 1000,
          },
          mutations: {
            // Retry failed mutations once
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <SessionContextProvider supabaseClient={supabase} initialSession={initialSession}>
        <AuthProvider>
          {children}
          {/* Only show devtools in development */}
          {process.env.NODE_ENV === "development" && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </AuthProvider>
      </SessionContextProvider>
    </QueryClientProvider>
  );
}
