import { vi } from "vitest";

type ToastProps = Record<string, unknown>;

export const mockToast = vi.fn((_props: ToastProps = {}) => ({
  dismiss: vi.fn(),
  id: `toast-${Date.now()}`,
  update: vi.fn(),
}));

export const mockUseToast = vi.fn(() => ({
  dismiss: vi.fn(),
  toast: mockToast,
  toasts: [],
}));

export const resetToastMocks = () => {
  mockToast.mockClear();
  mockUseToast.mockClear();
};
