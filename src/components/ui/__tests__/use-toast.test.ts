/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";

import { toast, useToast } from "../use-toast";

/**
 * Tests for the Sonner toast wrapper API shape.
 *
 * Note: These tests verify the public API shape without mocking Sonner internals.
 * The actual Sonner calls are verified through manual testing and build validation.
 */
describe("use-toast compatibility wrapper", () => {
  describe("toast()", () => {
    it("is a function", () => {
      expect(typeof toast).toBe("function");
    });

    it("returns id, dismiss, and update functions", () => {
      const result = toast({ title: "Test" });

      expect(result).toHaveProperty("id");
      expect(result).toHaveProperty("dismiss");
      expect(result).toHaveProperty("update");
      expect(typeof result.dismiss).toBe("function");
      expect(typeof result.update).toBe("function");
    });

    it("accepts title and description", () => {
      // Should not throw
      expect(() => {
        toast({ description: "Done", title: "Success" });
      }).not.toThrow();
    });

    it("accepts destructive variant", () => {
      // Should not throw
      expect(() => {
        toast({ description: "Failed", title: "Error", variant: "destructive" });
      }).not.toThrow();
    });

    it("accepts action prop", () => {
      // Should not throw
      expect(() => {
        toast({
          action: { label: "Undo", onClick: () => undefined },
          title: "Action toast",
        });
      }).not.toThrow();
    });
  });

  describe("useToast()", () => {
    it("returns toast function", () => {
      const { toast: toastFn } = useToast();

      expect(typeof toastFn).toBe("function");
    });

    it("returns dismiss function", () => {
      const { dismiss } = useToast();

      expect(typeof dismiss).toBe("function");
    });

    it("returns empty toasts array for compatibility", () => {
      const { toasts } = useToast();

      expect(toasts).toEqual([]);
    });

    it("dismiss does not throw when called with id", () => {
      const { dismiss } = useToast();

      expect(() => {
        dismiss("some-id");
      }).not.toThrow();
    });

    it("dismiss does not throw when called without id", () => {
      const { dismiss } = useToast();

      expect(() => {
        dismiss();
      }).not.toThrow();
    });
  });
});
