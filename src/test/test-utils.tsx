import type { QueryClient } from "@tanstack/react-query";
import { QueryClientProvider } from "@tanstack/react-query";
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import type { ComponentProps, ReactElement, ReactNode } from "react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { getTestQueryClient, resetTestQueryClient } from "./helpers/query-client";

type ThemeProviderProps = ComponentProps<typeof ThemeProvider>;

const DEFAULT_THEME: ThemeProviderProps = {
  attribute: "class",
  defaultTheme: "system",
  disableTransitionOnChange: true,
  enableSystem: true,
};

export { getTestQueryClient, resetTestQueryClient };

// Props for the AllTheProviders component.
export interface ProvidersProps {
  // The child components to render.
  children: ReactNode;
  // Optional theme configuration.
  theme?: ThemeProviderProps;
  // Optional QueryClient instance.
  queryClient?: QueryClient;
}

// Options for renderWithProviders function.
export interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  /** Optional theme configuration. */
  theme?: ProvidersProps["theme"];
  /** Optional QueryClient instance. */
  queryClient?: ProvidersProps["queryClient"];
}

// biome-ignore lint/style/useNamingConvention: React components should be PascalCase
export const AllTheProviders = ({
  children,
  theme = DEFAULT_THEME,
  queryClient,
}: ProvidersProps): ReactElement => {
  const client = queryClient ?? getTestQueryClient();

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider {...theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  );
};

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
