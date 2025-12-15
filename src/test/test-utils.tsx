import {
  type ValidatedThemeProviderProps,
  validateThemeProviderProps,
} from "@schemas/ui/theme-provider";
import type { QueryClient } from "@tanstack/react-query";
import { QueryClientProvider } from "@tanstack/react-query";
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import type { ComponentProps, ReactElement, ReactNode } from "react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { createMockQueryClient } from "./helpers/query";

// Type for next-themes provider props.
type NextThemesProviderProps = ComponentProps<typeof ThemeProvider>;

// Shared QueryClient for performance (cleared between tests via resetTestQueryClient)
let sharedQueryClient: QueryClient | null = null;

/**
 * Returns a shared test QueryClient with disabled retries and caching.
 * Call resetTestQueryClient() in afterEach to clear caches between tests.
 *
 * @returns A configured QueryClient for testing.
 */
export const getTestQueryClient = (): QueryClient => {
  if (!sharedQueryClient) {
    sharedQueryClient = createMockQueryClient();
  }
  return sharedQueryClient;
};

/**
 * Clears query and mutation caches on the shared QueryClient.
 * Call in afterEach() to ensure test isolation.
 */
export const resetTestQueryClient = (): void => {
  if (!sharedQueryClient) return;
  sharedQueryClient.getQueryCache?.().clear?.();
  sharedQueryClient.getMutationCache?.().clear?.();
};

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

// Explicit re-exports from testing-library (commonly used across tests)
export { fireEvent, screen, waitFor, within } from "@testing-library/react";
export { renderWithProviders as render };
