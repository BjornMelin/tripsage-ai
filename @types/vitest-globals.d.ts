/**
 * @fileoverview Global Vitest types.
 *
 * The repo sets `typeRoots`, so Vitest's bundled globals are not auto-included.
 * Importing `vitest/globals` here restores `describe/it/expect` typing.
 */

import "vitest/globals";
