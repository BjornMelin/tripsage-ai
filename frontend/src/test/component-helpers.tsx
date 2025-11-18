/**
 * @fileoverview Centralized component test helpers.
 *
 * Provides reusable utilities for testing React components:
 * - Custom render with providers
 * - Async state waiting utilities
 */

import { type RenderOptions, render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

/**
 * Custom render with providers.
 *
 * @param ui - React element to render
 * @param options - Render options
 * @returns Render result
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <>{children}</>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

/**
 * Wait for async state updates.
 *
 * @returns Promise that resolves after next tick
 */
export async function waitForAsync(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}
