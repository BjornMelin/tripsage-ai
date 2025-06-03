"use client";

import { getCurrentUser, logoutAction, type User } from "@/lib/auth/server-actions";
import { useRouter } from "next/navigation";
import type React from "react";
import {
  createContext,
  useContext,
  useEffect,
  useOptimistic,
  startTransition,
} from "react";

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

  // React 19 optimistic state management
  const [authState, setAuthState] = useOptimistic<AuthState>(
    {
      user: initialUser,
      isAuthenticated: !!initialUser,
      isLoading: !initialUser,
      error: null,
    },
    (currentState, optimisticValue: Partial<AuthState>) => ({
      ...currentState,
      ...optimisticValue,
    })
  );

  // Load user on mount if not provided
  useEffect(() => {
    if (!initialUser) {
      refreshUser();
    }
  }, [initialUser]);

  // Refresh user data from server
  const refreshUser = async () => {
    try {
      setAuthState({ isLoading: true, error: null });

      const user = await getCurrentUser();

      startTransition(() => {
        setAuthState({
          user,
          isAuthenticated: !!user,
          isLoading: false,
          error: null,
        });
      });
    } catch (error) {
      console.error("Failed to refresh user:", error);
      startTransition(() => {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: "Failed to load user data",
        });
      });
    }
  };

  // Login function (optimistic)
  const login = (user: User) => {
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
    try {
      // Optimistically clear user state
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });

      // Call server action to clear cookie
      await logoutAction();

      // Note: logoutAction redirects to "/" automatically
    } catch (error) {
      console.error("Logout failed:", error);
      setAuthState({
        error: "Failed to logout. Please try again.",
      });

      // Manual redirect on error
      router.push("/");
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

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        const redirectUrl = options?.redirectTo || "/login";
        router.push(redirectUrl);
      }
    }, [isLoading, isAuthenticated, router]);

    // Show loading state while checking authentication
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      );
    }

    // Don't render component if not authenticated
    if (!isAuthenticated) {
      return null;
    }

    // Check role-based access if specified
    if (options?.allowedRoles && user) {
      // This is a placeholder - implement role checking based on your user model
      // if (!options.allowedRoles.includes(user.role)) {
      //   return <div>Access Denied</div>;
      // }
    }

    return <Component {...props} />;
  };
}

// Server component helper to get initial user
export async function getServerUser(): Promise<User | null> {
  try {
    return await getCurrentUser();
  } catch (error) {
    console.error("Failed to get server user:", error);
    return null;
  }
}
