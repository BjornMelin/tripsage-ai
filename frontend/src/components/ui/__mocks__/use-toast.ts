/**
 * @fileoverview Vitest mocks for the use-toast module. Provides mocked
 * implementations for testing toast functionality in isolation.
 */

import { vi } from "vitest";
import type { Toast } from "../use-toast";

/**
 * Mock implementation of the toast function. Creates a mock toast object
 * with jest mock functions for testing purposes.
 *
 * @param _props - Toast properties (ignored in mock).
 * @returns A mock toast object with dismiss, id, and update properties.
 */
export const toast = vi.fn((_props: Toast) => ({
  dismiss: vi.fn(),
  id: `toast-${Date.now()}`,
  update: vi.fn(),
}));

/**
 * Mock implementation of the useToast hook. Returns a mock object
 * with the expected hook interface for testing.
 *
 * @returns A mock useToast hook result with dismiss function, toast function, and empty toasts array.
 */
export const useToast = vi.fn(() => ({
  dismiss: vi.fn(),
  toast,
  toasts: [],
}));
