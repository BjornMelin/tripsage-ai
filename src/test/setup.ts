/**
 * @fileoverview Shared DOM shims used across Vitest projects.
 *
 * Some component libraries assume these DOM APIs exist; jsdom omits them.
 * Guarded so non-DOM test projects (e.g. node) can still load this file.
 */

if (typeof HTMLElement !== "undefined") {
  if (!HTMLElement.prototype.hasPointerCapture) {
    HTMLElement.prototype.hasPointerCapture = (_pointerId: number) => false;
  }

  if (!HTMLElement.prototype.releasePointerCapture) {
    HTMLElement.prototype.releasePointerCapture = (_pointerId: number) => undefined;
  }

  if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = (_arg?: boolean | ScrollIntoViewOptions) =>
      undefined;
  }
}
