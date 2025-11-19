import { describe, expect, it } from "vitest";
import { loginRequestSchema } from "../api";
import { budgetFormSchema } from "../budget";
import { loginFormSchema } from "../forms";
import { primitiveSchemas } from "../registry";

describe("schema integration", () => {
  describe("API and form schema consistency", () => {
    it.concurrent("should validate login data consistently between API and form schemas", () => {
      const loginData = {
        email: "test@example.com",
        password: "password123",
      };

      const apiResult = loginRequestSchema.safeParse(loginData);
      const formResult = loginFormSchema.safeParse(loginData);

      expect(apiResult.success).toBe(true);
      expect(formResult.success).toBe(true);
    });
  });

  describe("registry primitive usage", () => {
    it.concurrent("should use registry primitives in form schemas", () => {
      const emailResult = primitiveSchemas.email.safeParse("test@example.com");
      expect(emailResult.success).toBe(true);
    });

    it.concurrent("should use registry primitives in budget schemas", () => {
      const uuidResult = primitiveSchemas.uuid.safeParse(
        "123e4567-e89b-12d3-a456-426614174000"
      );
      expect(uuidResult.success).toBe(true);
    });
  });

  describe("form validation flow", () => {
    it.concurrent("should validate budget form with registry primitives", () => {
      const result = budgetFormSchema.safeParse({
        categories: [
          { amount: 2000, category: "flights" },
          { amount: 2000, category: "accommodations" },
          { amount: 1000, category: "food" },
        ],
        currency: "USD",
        name: "Summer Trip",
        totalAmount: 5000,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("error message consistency", () => {
    it.concurrent("should provide consistent error messages using unified error option", () => {
      const result = primitiveSchemas.email.safeParse("invalid-email");
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBeDefined();
      }
    });
  });
});
