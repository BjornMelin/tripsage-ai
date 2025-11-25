/** @vitest-environment node */

import type { AdvisoryProvider } from "@ai/tools/server/travel-advisory/providers";
import {
  getDefaultProvider,
  getProvider,
  providerRegistry,
  registerProvider,
} from "@ai/tools/server/travel-advisory/providers";
import { createStateDepartmentProvider } from "@ai/tools/server/travel-advisory/providers/state-department";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

describe("Provider Registry", () => {
  beforeEach(() => {
    providerRegistry.clear();
  });

  afterEach(() => {
    providerRegistry.clear();
  });

  describe("registerProvider", () => {
    test("registers a provider with its name", () => {
      const provider = createStateDepartmentProvider();
      registerProvider(provider);

      expect(providerRegistry.has("state_department")).toBe(true);
      expect(providerRegistry.get("state_department")).toBe(provider);
    });

    test("overwrites existing provider with same name", () => {
      const provider1 = createStateDepartmentProvider();
      const provider2 = createStateDepartmentProvider();

      registerProvider(provider1);
      registerProvider(provider2);

      expect(providerRegistry.get("state_department")).toBe(provider2);
      expect(providerRegistry.size).toBe(1);
    });

    test("registers multiple different providers", () => {
      const provider1 = createStateDepartmentProvider();
      const mockProvider: AdvisoryProvider = {
        getCountryAdvisory: async () => null,
        getProviderName: () => "mock_provider",
      };

      registerProvider(provider1);
      registerProvider(mockProvider);

      expect(providerRegistry.size).toBe(2);
      expect(providerRegistry.get("state_department")).toBe(provider1);
      expect(providerRegistry.get("mock_provider")).toBe(mockProvider);
    });
  });

  describe("getProvider", () => {
    test("returns registered provider by name", () => {
      const provider = createStateDepartmentProvider();
      registerProvider(provider);

      const retrieved = getProvider("state_department");
      expect(retrieved).toBe(provider);
    });

    test("returns undefined for unregistered provider", () => {
      const retrieved = getProvider("nonexistent");
      expect(retrieved).toBeUndefined();
    });

    test("returns undefined for empty string", () => {
      const retrieved = getProvider("");
      expect(retrieved).toBeUndefined();
    });
  });

  describe("getDefaultProvider", () => {
    test("returns state_department provider when registered", () => {
      const provider = createStateDepartmentProvider();
      registerProvider(provider);

      const defaultProvider = getDefaultProvider();
      expect(defaultProvider).toBe(provider);
      expect(defaultProvider?.getProviderName()).toBe("state_department");
    });

    test("returns undefined when no provider registered", () => {
      const defaultProvider = getDefaultProvider();
      expect(defaultProvider).toBeUndefined();
    });

    test("returns undefined when state_department not registered but others are", () => {
      const mockProvider: AdvisoryProvider = {
        getCountryAdvisory: async () => null,
        getProviderName: () => "other_provider",
      };
      registerProvider(mockProvider);

      const defaultProvider = getDefaultProvider();
      expect(defaultProvider).toBeUndefined();
    });
  });
});
