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
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
  root = null;
  rootMargin = "";
  thresholds = [];
};

// Mock matchMedia for tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

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
