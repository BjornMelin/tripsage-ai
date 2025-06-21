import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock ResizeObserver for tests
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver for tests
global.IntersectionObserver = class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
  root = null;
  rootMargin = "";
  thresholds = [];
};

// matchMedia is already mocked in test-setup.ts - removed duplicate

// Mock CSS.supports for tests
Object.defineProperty(global, "CSS", {
  value: {
    supports: vi.fn().mockReturnValue(false),
  },
});

// Mock zustand middleware
vi.mock("zustand/middleware", () => ({
  persist: vi.fn((fn: any) => fn),
  devtools: vi.fn((fn: any) => fn),
  subscribeWithSelector: vi.fn((fn: any) => fn),
  combine: vi.fn((fn: any) => fn),
}));
