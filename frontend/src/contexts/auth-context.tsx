"use client";

import { useSupabase } from "@/lib/supabase/client";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import type React from "react";
import { createContext, useContext, useEffect, useState } from "react";

// User type extending Supabase User with additional fields
export interface User {
  id: string;
  email: string;
  name?: string;
  full_name?: string;
  avatar_url?: string;
  created_at?: string;
  updated_at?: string;
}

// Authentication context types
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithOAuth: (provider: "google" | "github") => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  resetPassword: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
}

// Create the authentication context
const AuthContext = createContext<AuthContextType | null>(null);

// Custom hook to use the auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: React.ReactNode;
  initialUser?: User | null;
}

// Authentication state type for optimistic updates
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export function AuthProvider({ children, initialUser = null }: AuthProviderProps) {
  const router = useRouter();
  const supabase = useSupabase();

  // State management with Supabase Auth
  const [authState, setAuthStateInternal] = useState<AuthState>({
    user: initialUser,
    isAuthenticated: !!initialUser,
    isLoading: true,
    error: null,
  });

  const setAuthState = (update: Partial<AuthState>) => {
    setAuthStateInternal((prev) => ({ ...prev, ...update }));
  };

  // Convert Supabase user to our User type
  const convertSupabaseUser = (supabaseUser: SupabaseUser): User => ({
    id: supabaseUser.id,
    email: supabaseUser.email!,
    name: supabaseUser.user_metadata?.full_name || supabaseUser.email?.split("@")[0],
    full_name: supabaseUser.user_metadata?.full_name,
    avatar_url: supabaseUser.user_metadata?.avatar_url,
    created_at: supabaseUser.created_at,
    updated_at: supabaseUser.updated_at,
  });

  // Listen for auth state changes
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const user = convertSupabaseUser(session.user);
        setAuthState({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      }
    });

    // Get initial session
    supabase.auth.getSession().then(({ data: { session }, error }) => {
      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      if (session?.user) {
        const user = convertSupabaseUser(session.user);
        setAuthState({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      }
    });

    return () => subscription.unsubscribe();
  }, [supabase.auth]);

  // Refresh user data from server
  const refreshUser = async () => {
    try {
      setAuthState({ isLoading: true, error: null });
      const {
        data: { user },
        error,
      } = await supabase.auth.getUser();

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      if (user) {
        const convertedUser = convertSupabaseUser(user);
        setAuthState({
          user: convertedUser,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      }
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to refresh user",
        isLoading: false,
      });
    }
  };

  // Sign in function
  const signIn = async (email: string, password: string) => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { data: _data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      // User state will be updated by the auth state change listener
      setAuthState({ isLoading: false, error: null });
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to sign in",
        isLoading: false,
      });
    }
  };

  // Sign up function
  const signUp = async (email: string, password: string, fullName?: string) => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { data: _data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      // User state will be updated by the auth state change listener
      setAuthState({ isLoading: false, error: null });
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to sign up",
        isLoading: false,
      });
    }
  };

  // Sign in with OAuth provider
  const signInWithOAuth = async (provider: "google" | "github") => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { data: _data, error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          queryParams: {
            access_type: "offline",
            prompt: "consent",
          },
          // PKCE is enabled by default in Supabase Auth
          // Additional security options
          scopes: provider === "google" ? "openid email profile" : "user:email",
        },
      });

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      // The user will be redirected to the OAuth provider
      // State will be updated when they return via the auth state change listener
    } catch (error) {
      setAuthState({
        error:
          error instanceof Error ? error.message : `Failed to sign in with ${provider}`,
        isLoading: false,
      });
    }
  };

  // Sign out function
  const signOut = async () => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { error } = await supabase.auth.signOut();

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      // User state will be updated by the auth state change listener
      setAuthState({ isLoading: false, error: null });
      router.push("/");
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to sign out",
        isLoading: false,
      });
    }
  };

  // Reset password function
  const resetPassword = async (email: string) => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      setAuthState({ isLoading: false, error: null });
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to send reset email",
        isLoading: false,
      });
    }
  };

  // Update password function
  const updatePassword = async (newPassword: string) => {
    try {
      setAuthState({ isLoading: true, error: null });

      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        setAuthState({ error: error.message, isLoading: false });
        return;
      }

      setAuthState({ isLoading: false, error: null });
    } catch (error) {
      setAuthState({
        error: error instanceof Error ? error.message : "Failed to update password",
        isLoading: false,
      });
    }
  };

  // Clear error
  const clearError = () => {
    setAuthState({ error: null });
  };

  const contextValue: AuthContextType = {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    error: authState.error,
    signIn,
    signInWithOAuth,
    signUp,
    signOut,
    refreshUser,
    clearError,
    resetPassword,
    updatePassword,
  };

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

// Higher-order component for protected pages
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    redirectTo?: string;
    allowedRoles?: string[];
  }
) {
  return function ProtectedComponent(props: P) {
    const { user: _user, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        router.push(options?.redirectTo || "/login");
      }
    }, [isAuthenticated, isLoading, router, options?.redirectTo]);

    if (isLoading) {
      return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
      return null; // Will redirect via useEffect
    }

    return <Component {...props} />;
  };
}
