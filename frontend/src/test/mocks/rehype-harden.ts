/**
 * @fileoverview Minimal rehype-harden stub for tests to avoid ESM/CJS packaging issues
 * in downstream dependencies when running under Vitest.
 */

export default function rehypeHarden() {
  // Return a no-op transformer
  return (_tree: unknown) => {
    // no-op
  };
}
