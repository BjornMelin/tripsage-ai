/**
 * Comprehensive Zod schemas for form validation
 * Runtime validation for all form inputs and user data
 */

import { z } from "zod";

// Common validation patterns
const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(128, "Password too long")
  .regex(/^(?=.*[a-z])/, "Password must contain at least one lowercase letter")
  .regex(/^(?=.*[A-Z])/, "Password must contain at least one uppercase letter")
  .regex(/^(?=.*\d)/, "Password must contain at least one number")
  .regex(/^(?=.*[@$!%*?&])/, "Password must contain at least one special character");

const emailSchema = z
  .string()
  .min(1, "Email is required")
  .email("Please enter a valid email address")
  .max(255, "Email must be less than 255 characters");

const phoneSchema = z
  .string()
  .regex(/^\+?[\d\s\-\(\)]{10,20}$/, "Please enter a valid phone number")
  .optional();

const nameSchema = z
  .string()
  .min(1, "Name is required")
  .max(50, "Name too long")
  .regex(
    /^[a-zA-Z\s\-'\.]+$/,
    "Name can only contain letters, spaces, hyphens, apostrophes, and periods"
  );

const dateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Please enter a valid date (YYYY-MM-DD)")
  .refine(
    (date) => !Number.isNaN(new Date(date).getTime()),
    "Please enter a valid date"
  );

const futureDateSchema = dateSchema.refine(
  (date) => new Date(date) > new Date(),
  "Date must be in the future"
);

const currencySchema = z
  .string()
  .length(3, "Currency code must be 3 characters")
  .regex(/^[A-Z]{3}$/, "Currency code must be uppercase letters");

export const currencyCodeSchema = currencySchema;

// Authentication forms
export const loginFormSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Password is required").max(128, "Password too long"),
  rememberMe: z.boolean().optional(),
});

export const registerFormSchema = z
  .object({
    firstName: nameSchema,
    lastName: nameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
    acceptTerms: z
      .boolean()
      .refine((val) => val === true, "You must accept the terms and conditions"),
    marketingOptIn: z.boolean().optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const resetPasswordFormSchema = z.object({
  email: emailSchema,
});

export const confirmResetPasswordFormSchema = z
  .object({
    token: z.string().min(1, "Reset token is required"),
    newPassword: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const changePasswordFormSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    message: "New password must be different from current password",
    path: ["newPassword"],
  });

// Profile forms
export const personalInfoFormSchema = z.object({
  firstName: nameSchema,
  lastName: nameSchema,
  displayName: z.string().max(100, "Display name too long").optional(),
  bio: z.string().max(500, "Bio too long").optional(),
  dateOfBirth: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Please enter a valid date")
    .refine((date) => {
      const birthDate = new Date(date);
      const today = new Date();
      const age = today.getFullYear() - birthDate.getFullYear();
      return age >= 13 && age <= 120;
    }, "You must be between 13 and 120 years old")
    .optional(),
  phoneNumber: phoneSchema,
  timezone: z.string().optional(),
  language: z.string().min(2).max(5).optional(),
  currency: currencySchema.optional(),
});

export const preferencesFormSchema = z.object({
  emailNotifications: z.boolean(),
  pushNotifications: z.boolean(),
  smsNotifications: z.boolean(),
  marketingEmails: z.boolean(),
  weeklyDigest: z.boolean(),
  travelDeals: z.boolean(),
  theme: z.enum(["light", "dark", "system"]),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]),
  timeFormat: z.enum(["12h", "24h"]),
  defaultCurrency: currencySchema,
  defaultLanguage: z.string().min(2).max(5),
});

export const securitySettingsFormSchema = z.object({
  twoFactorEnabled: z.boolean(),
  backupCodesGenerated: z.boolean().optional(),
  trustedDevices: z.array(z.string()).optional(),
  sessionTimeout: z.number().int().positive().max(43200), // Max 12 hours
  loginAlerts: z.boolean(),
});

// Search forms
export const flightSearchFormSchema = z
  .object({
    tripType: z.enum(["round-trip", "one-way", "multi-city"]),
    origin: z.string().min(1, "Departure location is required"),
    destination: z.string().min(1, "Destination is required"),
    departureDate: futureDateSchema,
    returnDate: futureDateSchema.optional(),
    passengers: z.object({
      adults: z
        .number()
        .int()
        .min(1, "At least 1 adult required")
        .max(20, "Too many passengers"),
      children: z.number().int().min(0).max(20, "Too many passengers"),
      infants: z.number().int().min(0).max(20, "Too many passengers"),
    }),
    cabinClass: z.enum(["economy", "premium_economy", "business", "first"]),
    directOnly: z.boolean(),
    maxStops: z.number().int().min(0).max(3).optional(),
    preferredAirlines: z.array(z.string()).optional(),
    excludedAirlines: z.array(z.string()).optional(),
  })
  .refine(
    (data) => {
      if (data.tripType === "round-trip" && !data.returnDate) {
        return false;
      }
      return true;
    },
    {
      message: "Return date is required for round-trip flights",
      path: ["returnDate"],
    }
  )
  .refine(
    (data) => {
      if (data.returnDate && data.departureDate) {
        return new Date(data.returnDate) > new Date(data.departureDate);
      }
      return true;
    },
    {
      message: "Return date must be after departure date",
      path: ["returnDate"],
    }
  );

export const accommodationSearchFormSchema = z
  .object({
    destination: z.string().min(1, "Destination is required"),
    checkIn: futureDateSchema,
    checkOut: futureDateSchema,
    guests: z.object({
      adults: z
        .number()
        .int()
        .min(1, "At least 1 adult required")
        .max(20, "Too many guests"),
      children: z.number().int().min(0).max(20, "Too many guests"),
      infants: z.number().int().min(0).max(20, "Too many guests"),
    }),
    rooms: z
      .number()
      .int()
      .min(1, "At least 1 room required")
      .max(20, "Too many rooms"),
    propertyType: z
      .enum(["hotel", "apartment", "villa", "hostel", "resort"])
      .optional(),
    priceRange: z
      .object({
        min: z.number().min(0, "Minimum price cannot be negative").optional(),
        max: z.number().positive("Maximum price must be positive").optional(),
      })
      .refine(
        (data) => {
          if (data.min && data.max) {
            return data.min <= data.max;
          }
          return true;
        },
        {
          message: "Minimum price must be less than or equal to maximum price",
          path: ["min"],
        }
      )
      .optional(),
    amenities: z.array(z.string()).optional(),
    minRating: z.number().min(0).max(5).optional(),
  })
  .refine((data) => new Date(data.checkOut) > new Date(data.checkIn), {
    message: "Check-out date must be after check-in date",
    path: ["checkOut"],
  });

export const activitySearchFormSchema = z.object({
  destination: z.string().min(1, "Destination is required"),
  date: futureDateSchema.optional(),
  dateRange: z
    .object({
      start: futureDateSchema,
      end: futureDateSchema,
    })
    .refine((data) => new Date(data.end) > new Date(data.start), {
      message: "End date must be after start date",
      path: ["end"],
    })
    .optional(),
  participants: z.object({
    adults: z
      .number()
      .int()
      .min(1, "At least 1 adult required")
      .max(50, "Too many participants"),
    children: z.number().int().min(0).max(50, "Too many participants"),
  }),
  category: z.string().optional(),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  duration: z
    .object({
      min: z.number().positive().optional(),
      max: z.number().positive().optional(),
    })
    .refine(
      (data) => {
        if (data.min && data.max) {
          return data.min <= data.max;
        }
        return true;
      },
      {
        message: "Minimum duration must be less than or equal to maximum duration",
        path: ["min"],
      }
    )
    .optional(),
  priceRange: z
    .object({
      min: z.number().min(0).optional(),
      max: z.number().positive().optional(),
    })
    .refine(
      (data) => {
        if (data.min && data.max) {
          return data.min <= data.max;
        }
        return true;
      },
      {
        message: "Minimum price must be less than or equal to maximum price",
        path: ["min"],
      }
    )
    .optional(),
  indoor: z.boolean().optional(),
});

// Trip forms
export const createTripFormSchema = z
  .object({
    title: z.string().min(1, "Trip title is required").max(200, "Title too long"),
    description: z.string().max(1000, "Description too long").optional(),
    destination: z.string().min(1, "Destination is required"),
    startDate: futureDateSchema,
    endDate: futureDateSchema,
    budget: z
      .object({
        total: z.number().positive("Budget must be positive"),
        currency: currencySchema,
      })
      .optional(),
    travelers: z
      .array(
        z.object({
          name: nameSchema,
          email: emailSchema.optional(),
          ageGroup: z.enum(["adult", "child", "infant"]).optional(),
          role: z.enum(["owner", "collaborator", "viewer"]).optional(),
        })
      )
      .min(1, "At least one traveler is required")
      .max(20, "Too many travelers"),
    isPublic: z.boolean(),
    allowCollaboration: z.boolean(),
    tags: z.array(z.string().max(50)).max(10).optional(),
  })
  .refine((data) => new Date(data.endDate) > new Date(data.startDate), {
    message: "End date must be after start date",
    path: ["endDate"],
  });

export const updateTripFormSchema = z.object({
  id: z.string().uuid(),
  title: z.string().optional(),
  description: z.string().optional(),
  destination: z.string().optional(),
  startDate: z.string().date().optional(),
  endDate: z.string().date().optional(),
  budget: z.number().optional(),
  isPublic: z.boolean().optional(),
  maxParticipants: z.number().optional(),
  tags: z.array(z.string()).optional(),
});

export const addTravelerFormSchema = z.object({
  name: nameSchema,
  email: emailSchema.optional(),
  ageGroup: z.enum(["adult", "child", "infant"]),
  role: z.enum(["collaborator", "viewer"]),
  sendInvitation: z.boolean(),
});

// Budget forms
export const expenseFormSchema = z.object({
  amount: z.number().positive("Amount must be positive"),
  currency: currencySchema,
  category: z.string().min(1, "Category is required"),
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  date: dateSchema,
  location: z.string().max(100).optional(),
  receipt: z.string().url("Invalid receipt URL").optional(),
  tags: z.array(z.string().max(50)).max(5).optional(),
});

export const budgetCategoryFormSchema = z.object({
  name: z.string().min(1, "Category name is required").max(50, "Name too long"),
  allocated: z.number().min(0, "Allocated amount cannot be negative"),
  currency: currencySchema,
  color: z
    .string()
    .regex(/^#[0-9A-F]{6}$/i, "Invalid color format")
    .optional(),
  icon: z.string().optional(),
});

// Chat forms
export const sendMessageFormSchema = z.object({
  message: z.string().min(1, "Message cannot be empty").max(10000, "Message too long"),
  conversationId: z.string().uuid().optional(),
  attachments: z
    .array(
      z.object({
        type: z.enum(["image", "document", "audio", "video"]),
        file: z.any(), // File object
        name: z.string().min(1),
        size: z
          .number()
          .positive()
          .max(50 * 1024 * 1024), // 50MB max
      })
    )
    .max(5, "Too many attachments")
    .optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const createConversationFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(200, "Title too long"),
  initialMessage: z
    .string()
    .min(1, "Initial message is required")
    .max(10000, "Message too long"),
  participants: z.array(z.string().uuid()).optional(),
  isPrivate: z.boolean(),
});

// API Key forms
export const apiKeyFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name too long"),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
  key: z
    .string()
    .min(1, "API key is required")
    .max(500, "API key too long")
    .regex(/^[a-zA-Z0-9\-_\.]+$/, "Invalid API key format"),
  description: z.string().max(200, "Description too long").optional(),
});

// Contact forms
export const contactFormSchema = z.object({
  name: nameSchema,
  email: emailSchema,
  subject: z.string().min(1, "Subject is required").max(200, "Subject too long"),
  message: z
    .string()
    .min(10, "Message must be at least 10 characters")
    .max(2000, "Message too long"),
  category: z.enum(["support", "feedback", "bug", "feature", "other"]),
  urgency: z.enum(["low", "medium", "high"]),
});

export const feedbackFormSchema = z.object({
  rating: z
    .number()
    .int()
    .min(1, "Please provide a rating")
    .max(5, "Rating must be between 1 and 5"),
  title: z.string().min(1, "Title is required").max(100, "Title too long"),
  description: z
    .string()
    .min(10, "Please provide more details")
    .max(1000, "Description too long"),
  category: z.enum(["ui", "performance", "feature", "bug", "other"]),
  anonymous: z.boolean(),
  email: z.string().email().optional(),
});

// Newsletter forms
export const newsletterSubscriptionFormSchema = z.object({
  email: emailSchema,
  preferences: z.object({
    weeklyDigest: z.boolean(),
    travelDeals: z.boolean(),
    newFeatures: z.boolean(),
    tips: z.boolean(),
  }),
  frequency: z.enum(["daily", "weekly", "monthly"]),
});

// Form validation utilities
export const validateFormData = <T>(schema: z.ZodSchema<T>, data: unknown): T => {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(
        `Form validation failed: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

export const safeValidateFormData = <T>(schema: z.ZodSchema<T>, data: unknown) => {
  return schema.safeParse(data);
};

export const getFormErrors = (error: z.ZodError) => {
  return error.issues.reduce(
    (acc, issue) => {
      const path = issue.path.join(".");
      acc[path] = issue.message;
      return acc;
    },
    {} as Record<string, string>
  );
};

// Type exports
export type LoginFormData = z.infer<typeof loginFormSchema>;
export type RegisterFormData = z.infer<typeof registerFormSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordFormSchema>;
export type ConfirmResetPasswordFormData = z.infer<
  typeof confirmResetPasswordFormSchema
>;
export type ChangePasswordFormData = z.infer<typeof changePasswordFormSchema>;
export type PersonalInfoFormData = z.infer<typeof personalInfoFormSchema>;
export type PreferencesFormData = z.infer<typeof preferencesFormSchema>;
export type SecuritySettingsFormData = z.infer<typeof securitySettingsFormSchema>;
export type FlightSearchFormData = z.infer<typeof flightSearchFormSchema>;
export type AccommodationSearchFormData = z.infer<typeof accommodationSearchFormSchema>;
export type ActivitySearchFormData = z.infer<typeof activitySearchFormSchema>;
export type CreateTripFormData = z.infer<typeof createTripFormSchema>;
export type UpdateTripFormData = z.infer<typeof updateTripFormSchema>;
export type AddTravelerFormData = z.infer<typeof addTravelerFormSchema>;
export type ExpenseFormData = z.infer<typeof expenseFormSchema>;
export type BudgetCategoryFormData = z.infer<typeof budgetCategoryFormSchema>;
export type SendMessageFormData = z.infer<typeof sendMessageFormSchema>;
export type CreateConversationFormData = z.infer<typeof createConversationFormSchema>;
export type ApiKeyFormData = z.infer<typeof apiKeyFormSchema>;
export type ContactFormData = z.infer<typeof contactFormSchema>;
export type FeedbackFormData = z.infer<typeof feedbackFormSchema>;
export type NewsletterSubscriptionFormData = z.infer<
  typeof newsletterSubscriptionFormSchema
>;
