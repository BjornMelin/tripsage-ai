import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import type { ComponentProps, ReactElement, ReactNode } from "react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import {
  type ValidatedThemeProviderProps,
  validateThemeProviderProps,
} from "@/lib/schemas/theme-provider";

// Type for next-themes provider props.
type NextThemesProviderProps = ComponentProps<typeof ThemeProvider>;

// Shared QueryClient instance for all tests (reset between tests)
let sharedQueryClient: QueryClient | null = null;

/**
 * Gets or creates the shared test QueryClient with disabled retries and caching.
 * This client is reused across tests for better performance and is cleared after
 * each test via resetTestQueryClient().
 *
 * @returns A configured QueryClient for testing.
 */
export const getTestQueryClient = (): QueryClient => {
  if (!sharedQueryClient) {
    sharedQueryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: 0, retry: false, staleTime: 0 },
      },
    });
  }
  return sharedQueryClient;
};

/**
 * Clears the shared QueryClient cache without recreating the instance.
 * Called automatically after each test to ensure test isolation.
 */
export const resetTestQueryClient = (): void => {
  if (!sharedQueryClient) {
    return;
  }

  if (typeof sharedQueryClient.clear === "function") {
    sharedQueryClient.clear();
    return;
  }

  sharedQueryClient.getQueryCache?.().clear?.();
  sharedQueryClient.getMutationCache?.().clear?.();
};

/**
 * Creates a test QueryClient with disabled retries and caching.
 * @deprecated Use getTestQueryClient() instead for better performance.
 * @returns A configured QueryClient for testing.
 */
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { gcTime: 0, retry: false, staleTime: 0 },
    },
  });

// Props for the AllTheProviders component.
export interface ProvidersProps {
  // The child components to render.
  children: ReactNode;
  // Optional theme configuration.
  theme?: ValidatedThemeProviderProps;
  // Optional QueryClient instance.
  queryClient?: QueryClient;
}

// Options for renderWithProviders function.
export interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  /** Optional theme configuration. */
  theme?: ProvidersProps["theme"];
  /** Optional QueryClient instance. */
  queryClient?: QueryClient;
}

/**
 * Component that provides all necessary providers for testing.
 * @param props The props for the providers.
 * @returns JSX element with providers wrapped around children.
 */
// biome-ignore lint/style/useNamingConvention: React components should be PascalCase
export const AllTheProviders = ({
  children,
  theme = {
    attribute: "class" as const,
    defaultTheme: "system",
    disableTransitionOnChange: true,
    enableSystem: true,
  },
  queryClient,
}: ProvidersProps): ReactElement => {
  const client = queryClient || getTestQueryClient();

  // Skip validation if using default theme for better performance
  const validatedTheme = theme
    ? (() => {
        const result = validateThemeProviderProps(theme);
        if (!result.success) {
          console.warn("Invalid theme configuration in test:", result.error.issues);
          return {
            attribute: "class" as const,
            defaultTheme: "system",
            disableTransitionOnChange: true,
            enableSystem: true,
          };
        }
        return result.data;
      })()
    : undefined;

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider
        {...((validatedTheme ?? {
          attribute: "class" as const,
          defaultTheme: "system",
          disableTransitionOnChange: true,
          enableSystem: true,
        }) as NextThemesProviderProps)}
      >
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

/**
 * Renders a React element with all necessary providers.
 * @param ui The React element to render.
 * @param options Options for rendering, including theme and query client.
 * @returns The rendered result from testing-library.
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
