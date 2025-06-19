import { vi } from "vitest";

export const mockToast = vi.fn((props: any) => ({
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
