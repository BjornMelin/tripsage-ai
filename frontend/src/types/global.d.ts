/// <reference types="vitest" />

import type { RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import type { RenderWithProvidersOptions } from "../test/test-utils.test";

// Extend Vitest types to include environment stubbing methods
declare module "vitest" {
  interface VitestUtils {
    stubEnv(key: string, value: string): void;
    unstubAllEnvs(): void;
  }
}

declare global {
  /**
   * Global render helper for tests with providers
   */
  var renderWithProviders: (
    ui: ReactElement,
    options?: RenderWithProvidersOptions
  ) => RenderResult;

  // Extend NodeJS global if needed
  namespace NodeJs {
    interface Global {
      renderWithProviders: typeof renderWithProviders;
    }
  }
}
