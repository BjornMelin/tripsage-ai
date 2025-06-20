/// <reference types="vitest" />

import type { RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import type { RenderWithProvidersOptions } from "../test/test-utils";

declare global {
  /**
   * Global render helper for tests with providers
   */
  var renderWithProviders: (
    ui: ReactElement,
    options?: RenderWithProvidersOptions
  ) => RenderResult;

  // Extend NodeJS global if needed
  namespace NodeJS {
    interface Global {
      renderWithProviders: typeof renderWithProviders;
    }
  }
}
