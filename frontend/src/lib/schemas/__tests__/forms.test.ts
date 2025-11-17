import { describe, expect, it } from "vitest";
import {
  accommodationSearchFormSchema,
  activitySearchFormSchema,
  changePasswordFormSchema,
  confirmResetPasswordFormSchema,
  contactFormSchema,
  createTripFormSchema,
  emailUpdateFormSchema,
  expenseFormSchema,
  flightSearchFormSchema,
  loginFormSchema,
  personalInfoFormSchema,
  preferencesFormSchema,
  registerFormSchema,
  resetPasswordFormSchema,
  sendMessageFormSchema,
} from "../forms";

describe("forms schemas", () => {
  describe("loginFormSchema", () => {
    it.concurrent("should validate valid login form", () => {
      const result = loginFormSchema.safeParse({
        email: "test@example.com",
        password: "password123",
        rememberMe: true,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid email", () => {
      const result = loginFormSchema.safeParse({
        email: "invalid-email",
        password: "password123",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject empty password", () => {
      const result = loginFormSchema.safeParse({
        email: "test@example.com",
        password: "",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("registerFormSchema", () => {
    it.concurrent("should validate valid registration form", () => {
      const result = registerFormSchema.safeParse({
        acceptTerms: true,
        confirmPassword: "Secure123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Secure123!",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject mismatched passwords", () => {
      const result = registerFormSchema.safeParse({
        acceptTerms: true,
        confirmPassword: "Different123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Secure123!",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject without accepting terms", () => {
      const result = registerFormSchema.safeParse({
        acceptTerms: false,
        confirmPassword: "Secure123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Secure123!",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject weak password", () => {
      const result = registerFormSchema.safeParse({
        acceptTerms: true,
        confirmPassword: "weak",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "weak",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("resetPasswordFormSchema", () => {
    it.concurrent("should validate reset password form", () => {
      const result = resetPasswordFormSchema.safeParse({
        email: "test@example.com",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid email", () => {
      const result = resetPasswordFormSchema.safeParse({
        email: "invalid-email",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("confirmResetPasswordFormSchema", () => {
    it.concurrent("should validate confirm reset password form", () => {
      const result = confirmResetPasswordFormSchema.safeParse({
        confirmPassword: "Secure123!",
        newPassword: "Secure123!",
        token: "reset-token-123",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject mismatched passwords", () => {
      const result = confirmResetPasswordFormSchema.safeParse({
        confirmPassword: "Different123!",
        newPassword: "Secure123!",
        token: "reset-token-123",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("changePasswordFormSchema", () => {
    it.concurrent("should validate change password form", () => {
      const result = changePasswordFormSchema.safeParse({
        confirmPassword: "Secure123!",
        currentPassword: "OldPassword123!",
        newPassword: "Secure123!",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject when new password matches current", () => {
      const result = changePasswordFormSchema.safeParse({
        confirmPassword: "SamePassword123!",
        currentPassword: "SamePassword123!",
        newPassword: "SamePassword123!",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("personalInfoFormSchema", () => {
    it.concurrent("should validate personal info form", () => {
      const result = personalInfoFormSchema.safeParse({
        displayName: "John Doe",
        firstName: "John",
        lastName: "Doe",
        phoneNumber: "+1234567890",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid name characters", () => {
      const result = personalInfoFormSchema.safeParse({
        firstName: "John123",
        lastName: "Doe",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("preferencesFormSchema", () => {
    it.concurrent("should validate preferences form", () => {
      const result = preferencesFormSchema.safeParse({
        currency: "USD",
        dateFormat: "MM/DD/YYYY",
        defaultCurrency: "USD",
        defaultLanguage: "en",
        emailNotifications: true,
        language: "en",
        marketingEmails: false,
        pushNotifications: true,
        smsNotifications: false,
        theme: "light",
        timeFormat: "12h",
        timezone: "America/New_York",
        travelDeals: false,
        units: "metric",
        weeklyDigest: false,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("emailUpdateFormSchema", () => {
    it.concurrent("should validate email update form", () => {
      const result = emailUpdateFormSchema.safeParse({
        email: "newemail@example.com",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid email", () => {
      const result = emailUpdateFormSchema.safeParse({
        email: "invalid-email",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("flightSearchFormSchema", () => {
    it.concurrent("should validate one-way flight search", () => {
      const futureDate = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = flightSearchFormSchema.safeParse({
        cabinClass: "economy",
        departureDate: futureDate,
        destination: "LAX",
        directOnly: false,
        origin: "JFK",
        passengers: {
          adults: 1,
          children: 0,
          infants: 0,
        },
        tripType: "one-way",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate round-trip flight search", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const result = flightSearchFormSchema.safeParse({
        cabinClass: "economy",
        departureDate: futureDate1,
        destination: "LAX",
        directOnly: false,
        origin: "JFK",
        passengers: {
          adults: 2,
          children: 1,
          infants: 0,
        },
        returnDate: futureDate2,
        tripType: "round-trip",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject round-trip without return date", () => {
      const futureDate = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = flightSearchFormSchema.safeParse({
        cabinClass: "economy",
        departureDate: futureDate,
        destination: "LAX",
        directOnly: false,
        origin: "JFK",
        passengers: {
          adults: 1,
          children: 0,
          infants: 0,
        },
        tripType: "round-trip",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject return date before departure", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = flightSearchFormSchema.safeParse({
        cabinClass: "economy",
        departureDate: futureDate1,
        destination: "LAX",
        directOnly: false,
        origin: "JFK",
        passengers: {
          adults: 1,
          children: 0,
          infants: 0,
        },
        returnDate: futureDate2,
        tripType: "round-trip",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("accommodationSearchFormSchema", () => {
    it.concurrent("should validate accommodation search form", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const result = accommodationSearchFormSchema.safeParse({
        checkIn: futureDate1,
        checkOut: futureDate2,
        destination: "Paris",
        guests: {
          adults: 2,
          children: 1,
          infants: 0,
        },
        rooms: 1,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject check-out before check-in", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = accommodationSearchFormSchema.safeParse({
        checkIn: futureDate1,
        checkOut: futureDate2,
        destination: "Paris",
        guests: {
          adults: 2,
          children: 0,
          infants: 0,
        },
        rooms: 1,
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject past dates", () => {
      const result = accommodationSearchFormSchema.safeParse({
        checkIn: "2020-01-01",
        checkOut: "2020-01-07",
        destination: "Paris",
        guests: {
          adults: 2,
          children: 0,
          infants: 0,
        },
        rooms: 1,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("activitySearchFormSchema", () => {
    it.concurrent("should validate activity search form", () => {
      const futureDate = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = activitySearchFormSchema.safeParse({
        category: "sightseeing",
        date: futureDate,
        destination: "Paris",
        participants: {
          adults: 1,
          children: 0,
        },
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate date range", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const result = activitySearchFormSchema.safeParse({
        dateRange: {
          end: futureDate2,
          start: futureDate1,
        },
        destination: "Paris",
        participants: {
          adults: 1,
          children: 0,
        },
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid date range", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const result = activitySearchFormSchema.safeParse({
        dateRange: {
          end: futureDate2,
          start: futureDate1,
        },
        destination: "Paris",
        participants: {
          adults: 1,
          children: 0,
        },
      });
      expect(result.success).toBe(false);
    });
  });

  describe("createTripFormSchema", () => {
    it.concurrent("should validate create trip form", () => {
      const futureDate1 = new Date(Date.now() + 86400000 * 30)
        .toISOString()
        .split("T")[0];
      const futureDate2 = new Date(Date.now() + 86400000 * 37)
        .toISOString()
        .split("T")[0];
      const result = createTripFormSchema.safeParse({
        allowCollaboration: false,
        destination: "Paris",
        endDate: futureDate2,
        isPublic: false,
        startDate: futureDate1,
        title: "Summer Trip",
        travelers: [
          {
            name: "John Doe",
          },
        ],
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject end date before start date", () => {
      const result = createTripFormSchema.safeParse({
        budget: 5000,
        currency: "USD",
        destination: "Paris",
        endDate: "2024-06-01",
        startDate: "2024-06-07",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("expenseFormSchema", () => {
    it.concurrent("should validate expense form", () => {
      const result = expenseFormSchema.safeParse({
        amount: 100,
        category: "food",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative amount", () => {
      const result = expenseFormSchema.safeParse({
        amount: -100,
        category: "food",
        currency: "USD",
        date: "2024-06-01",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("sendMessageFormSchema", () => {
    it.concurrent("should validate send message form", () => {
      const result = sendMessageFormSchema.safeParse({
        message: "Hello",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject empty message", () => {
      const result = sendMessageFormSchema.safeParse({
        message: "",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("contactFormSchema", () => {
    it.concurrent("should validate contact form", () => {
      const result = contactFormSchema.safeParse({
        category: "support",
        email: "test@example.com",
        message: "Test message with at least 10 characters",
        name: "John Doe",
        subject: "Test subject",
        urgency: "medium",
      });
      expect(result.success).toBe(true);
    });
  });
});
