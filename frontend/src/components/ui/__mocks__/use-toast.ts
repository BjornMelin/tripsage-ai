import { vi } from "vitest";

export const toast = vi.fn((props: any) => ({
  id: `toast-${Date.now()}`,
  dismiss: vi.fn(),
  update: vi.fn(),
}));

export const useToast = vi.fn(() => ({
  toast,
  dismiss: vi.fn(),
  toasts: [],
}));
