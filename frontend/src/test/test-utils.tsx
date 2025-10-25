/**
 * @fileoverview Test utilities and providers for React component testing.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import type { ComponentProps, ReactElement, ReactNode } from "react";
import { vi } from "vitest";
import { ThemeProvider } from "@/components/providers/theme-provider";
import {
  type ValidatedThemeProviderProps,
  validateThemeProviderProps,
} from "@/schemas/theme-provider";

/** Type for next-themes provider props. */
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
      getUser: vi.fn(() => Promise.resolve({ data: { user: null } })),
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

/**
 * Creates a test QueryClient with disabled retries and caching.
 * @return A configured QueryClient for testing.
 */
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });

/** Props for the AllTheProviders component. */
export interface ProvidersProps {
  /** The child components to render. */
  children: ReactNode;
  /** Optional theme configuration. */
  theme?: ValidatedThemeProviderProps;
  /** Optional QueryClient instance. */
  queryClient?: QueryClient;
}

/** Options for renderWithProviders function. */
export interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  /** Optional theme configuration. */
  theme?: ProvidersProps["theme"];
  /** Optional QueryClient instance. */
  queryClient?: QueryClient;
}

/**
 * Component that provides all necessary providers for testing.
 * @param props The props for the providers.
 * @return JSX element with providers wrapped around children.
 */
export const AllTheProviders = ({
  children,
  theme = {
    attribute: "class" as const,
    defaultTheme: "system",
    enableSystem: true,
    disableTransitionOnChange: true,
  },
  queryClient,
}: ProvidersProps) => {
  const client = queryClient || createTestQueryClient();

  const validatedTheme = theme
    ? (() => {
        const result = validateThemeProviderProps(theme);
        if (!result.success) {
          console.warn("Invalid theme configuration in test:", result.error.issues);
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
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

/**
 * Renders a React element with all necessary providers.
 * @param ui The React element to render.
 * @param options Options for rendering, including theme and query client.
 * @return The rendered result from testing-library.
 */
export const renderWithProviders = (
  ui: ReactElement,
  { theme, queryClient, ...options }: RenderWithProvidersOptions = {}
) => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AllTheProviders theme={theme} queryClient={queryClient}>
      {children}
    </AllTheProviders>
  );
  return render(ui, { wrapper, ...options });
};

export * from "@testing-library/react";
export { renderWithProviders as render };
