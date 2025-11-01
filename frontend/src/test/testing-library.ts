/**
 * @fileoverview React Testing Library utilities and defaults.
 * Keep exports minimal; avoid global side-effects beyond RTL config.
 */

import { configure } from "@testing-library/react";

/**
 * Configure RTL defaults to reduce flakiness and warning noise.
 */
export function configureTestingLibrary(): void {
  configure({
    // Fail fast for async finders that never resolve
    asyncUtilTimeout: 4500,
  });
}
