import { vi } from "vitest";

type ToastProps = Record<string, unknown>;

export const mockToast = vi.fn((_props: ToastProps = {}) => ({
  id: `toast-${Date.now()}`,
  dismiss: vi.fn(),
  update: vi.fn(),
}));

export const mockUseToast = vi.fn(() => ({
  toast: mockToast,
  dismiss: vi.fn(),
  toasts: [],
}));

export const resetToastMocks = () => {
  mockToast.mockClear();
  mockUseToast.mockClear();
};
