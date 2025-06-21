import { ThemeProvider } from "@/components/providers/theme-provider";
import { AuthProvider } from "@/contexts/auth-context";
import type { User } from "@/contexts/auth-context";
import {
  type ValidatedThemeProviderProps,
  validateThemeProviderProps,
} from "@/schemas/theme-provider";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import type { ComponentProps } from "react";
import { vi } from "vitest";

// Type for next-themes provider props
type NextThemesProviderProps = ComponentProps<typeof ThemeProvider>;

// Mock the useSupabase hook for tests
vi.mock("@/lib/supabase/client", () => ({
  useSupabase: vi.fn(() => ({
    auth: {
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
      getSession: vi.fn(() =>
        Promise.resolve({ data: { session: null }, error: null })
      ),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      updateUser: vi.fn(),
      getUser: vi.fn(),
    },
  })),
  createClient: vi.fn(() => ({
    auth: {
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
      getSession: vi.fn(() =>
        Promise.resolve({ data: { session: null }, error: null })
      ),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        order: vi.fn(() => Promise.resolve({ data: [], error: null })),
      })),
      insert: vi.fn(() => ({
        select: vi.fn(() => ({
          single: vi.fn(() => Promise.resolve({ data: null, error: null })),
        })),
      })),
      update: vi.fn(() => ({
        eq: vi.fn(() => ({
          select: vi.fn(() => ({
            single: vi.fn(() => Promise.resolve({ data: null, error: null })),
          })),
        })),
      })),
      delete: vi.fn(() => ({
        eq: vi.fn(() => Promise.resolve({ error: null })),
      })),
    })),
  })),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  })),
  usePathname: vi.fn(() => "/"),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

// matchMedia is already mocked in test-setup.ts - no need to duplicate

// Create a custom render function that includes providers
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

export interface ProvidersProps {
  children: ReactNode;
  initialUser?: User | null;
  theme?: ValidatedThemeProviderProps;
  queryClient?: QueryClient;
}

export interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  initialUser?: User | null;
  theme?: ProvidersProps["theme"];
  queryClient?: QueryClient;
}

export const AllTheProviders = ({
  children,
  initialUser = null,
  theme = {
    attribute: "class" as const,
    defaultTheme: "system",
    enableSystem: true,
    disableTransitionOnChange: true,
  },
  queryClient,
}: ProvidersProps) => {
  const client = queryClient || createTestQueryClient();

  // Validate theme props if provided
  const validatedTheme = theme
    ? (() => {
        const result = validateThemeProviderProps(theme);
        if (!result.success) {
          console.warn("Invalid theme configuration in test:", result.error.issues);
          // Use default theme configuration on validation failure
          return {
            attribute: "class" as const,
            defaultTheme: "system",
            enableSystem: true,
            disableTransitionOnChange: true,
          };
        }
        return result.data;
      })()
    : undefined;

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider {...(validatedTheme as NextThemesProviderProps)}>
        <AuthProvider initialUser={initialUser}>{children}</AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export const renderWithProviders = (
  ui: ReactElement,
  { initialUser, theme, queryClient, ...options }: RenderWithProvidersOptions = {}
) => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AllTheProviders initialUser={initialUser} theme={theme} queryClient={queryClient}>
      {children}
    </AllTheProviders>
  );

  return render(ui, { wrapper, ...options });
};

// Helper function to create a mock authenticated user
export const createMockUser = (overrides?: Partial<User>): User => ({
  id: "test-user-id",
  email: "test@example.com",
  name: "Test User",
  full_name: "Test User",
  avatar_url: "https://example.com/avatar.jpg",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
});

// Create a default mock auth object
export const mockUseAuth = {
  user: null as User | null,
  isAuthenticated: false,
  isLoading: false,
  error: null as string | null,
  signIn: vi.fn(),
  signInWithOAuth: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  refreshUser: vi.fn(),
  clearError: vi.fn(),
  resetPassword: vi.fn(),
  updatePassword: vi.fn(),
};

// Mock the auth context
vi.mock("@/contexts/auth-context", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/contexts/auth-context")>();
  return {
    ...actual,
    useAuth: () => mockUseAuth,
  };
});

// Helper to mock auth state
export const mockAuthState = (
  user: User | null = null,
  isLoading = false,
  error: string | null = null
) => {
  // Update the mock values
  mockUseAuth.user = user;
  mockUseAuth.isAuthenticated = !!user;
  mockUseAuth.isLoading = isLoading;
  mockUseAuth.error = error;

  // Reset all mock functions
  Object.keys(mockUseAuth).forEach((key) => {
    if (typeof mockUseAuth[key as keyof typeof mockUseAuth] === "function") {
      (mockUseAuth[key as keyof typeof mockUseAuth] as any).mockClear();
    }
  });

  return mockUseAuth;
};

// Re-export everything
export * from "@testing-library/react";
export { renderWithProviders as render };
