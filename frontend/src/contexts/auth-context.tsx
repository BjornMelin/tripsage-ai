"use client";

// TODO: This is a temporary stub implementation pending Supabase Auth integration
// All JWT-related functionality has been removed

import { useRouter } from "next/navigation";
import type React from "react";
import { createContext, startTransition, useContext, useState } from "react";

// Temporary User type
export interface User {
  id: string;
  email: string;
  name?: string;
}

// Authentication context types
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (user: User) => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
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

  // State management - will be replaced with Supabase Auth state
  const [authState, setAuthStateInternal] = useState<AuthState>({
    user: null, // Temporarily always null until Supabase Auth is implemented
    isAuthenticated: false,
    isLoading: false,
    error: null,
  });

  const setAuthState = (update: Partial<AuthState>) => {
    setAuthStateInternal((prev) => ({ ...prev, ...update }));
  };

  // Refresh user data from server
  const refreshUser = async () => {
    // TODO: Implement with Supabase Auth
    console.log("refreshUser to be implemented with Supabase Auth");
    startTransition(() => {
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    });
  };

  // Login function (optimistic)
  const login = (user: User) => {
    // TODO: Implement with Supabase Auth
    console.log("login to be implemented with Supabase Auth");
    startTransition(() => {
      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    });
  };

  // Logout function
  const logout = async () => {
    // TODO: Implement with Supabase Auth
    console.log("logout to be implemented with Supabase Auth");
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    router.push("/");
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
    login,
    logout,
    refreshUser,
    clearError,
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
    const { user, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    // TODO: Implement proper authentication check with Supabase Auth
    // For now, allow access to all pages
    return <Component {...props} />;
  };
}

// Server component helper to get initial user
export async function getServerUser(): Promise<User | null> {
  // TODO: Implement with Supabase Auth
  return null;
}
