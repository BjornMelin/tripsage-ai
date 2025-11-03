import { vi } from "vitest";

export const toast = vi.fn((_props: any) => ({
  dismiss: vi.fn(),
  id: `toast-${Date.now()}`,
  update: vi.fn(),
}));

export const useToast = vi.fn(() => ({
  dismiss: vi.fn(),
  toast,
  toasts: [],
}));
