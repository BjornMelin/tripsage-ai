/**
 * @fileoverview Shared person/contact primitives (names, email, phone, password).
 */

import { z } from "zod";
import { primitiveSchemas, refinedSchemas } from "../registry";

export const NAME_SCHEMA = z
  .string()
  .min(1, { error: "Name is required" })
  .max(50, { error: "Name too long" })
  .regex(/^[a-zA-Z\s\-'.]+$/, {
    error: "Name can only contain letters, spaces, hyphens, apostrophes, and periods",
  });

export const EMAIL_SCHEMA = primitiveSchemas.email.max(255);

export const PHONE_SCHEMA = z
  .string()
  .regex(/^\+?[\d\s\-()]{10,20}$/, { error: "Please enter a valid phone number" });

export const PASSWORD_SCHEMA = refinedSchemas.strongPassword;

export type PersonName = z.infer<typeof NAME_SCHEMA>;
export type EmailAddress = z.infer<typeof EMAIL_SCHEMA>;
export type PhoneNumber = z.infer<typeof PHONE_SCHEMA>;
