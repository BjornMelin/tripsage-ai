"use server";

import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod";
import bcrypt from "bcryptjs";

// Environment variables with validation
const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "fallback-secret-for-development-only"
);

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
  maxAge: 60 * 60 * 24 * 7, // 7 days
  path: "/",
};

// Validation schemas using Zod
const LoginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

const RegisterSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
      "Password must contain uppercase, lowercase, number, and special character"
    ),
  name: z.string().min(2, "Name must be at least 2 characters"),
});

const ResetPasswordSchema = z.object({
  email: z.string().email("Invalid email address"),
});

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface JWTPayload {
  userId: string;
  email: string;
  name: string;
  iat: number;
  exp: number;
}

// Authentication state type for optimistic updates
export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// JWT utility functions
export async function createJWT(payload: Omit<JWTPayload, "iat" | "exp">) {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 60 * 60 * 24 * 7; // 7 days

  return await new SignJWT({ ...payload, iat, exp })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt(iat)
    .setExpirationTime(exp)
    .sign(JWT_SECRET);
}

export async function verifyJWT(token: string): Promise<JWTPayload | null> {
  try {
    const { payload } = await jwtVerify(token, JWT_SECRET);
    return payload as JWTPayload;
  } catch (error) {
    console.error("JWT verification failed:", error);
    return null;
  }
}

// Session management
export async function getSession(): Promise<JWTPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth-token")?.value;

  if (!token) {
    return null;
  }

  return await verifyJWT(token);
}

export async function getCurrentUser(): Promise<User | null> {
  const session = await getSession();
  
  if (!session) {
    return null;
  }

  // In a real app, you'd fetch from database
  // For now, return the user data from the JWT
  return {
    id: session.userId,
    email: session.email,
    name: session.name,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

export async function requireAuth(): Promise<User> {
  const user = await getCurrentUser();
  
  if (!user) {
    redirect("/login");
  }
  
  return user;
}

// Authentication Server Actions
export async function loginAction(
  prevState: any,
  formData: FormData
): Promise<{ success?: boolean; error?: string; user?: User }> {
  try {
    // Validate form data
    const rawData = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
    };

    const validatedData = LoginSchema.parse(rawData);

    // TODO: Replace with actual database lookup
    // This is a mock implementation for demonstration
    const mockUser = {
      id: "user-123",
      email: validatedData.email,
      name: "John Doe",
      hashedPassword: await bcrypt.hash("password123", 12), // Mock password
    };

    // Verify password
    const isValidPassword = await bcrypt.compare(
      validatedData.password,
      mockUser.hashedPassword
    );

    if (!isValidPassword) {
      return { error: "Invalid email or password" };
    }

    // Create JWT
    const token = await createJWT({
      userId: mockUser.id,
      email: mockUser.email,
      name: mockUser.name,
    });

    // Set secure cookie
    const cookieStore = await cookies();
    cookieStore.set("auth-token", token, COOKIE_OPTIONS);

    const user: User = {
      id: mockUser.id,
      email: mockUser.email,
      name: mockUser.name,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    return { success: true, user };
  } catch (error) {
    console.error("Login error:", error);
    
    if (error instanceof z.ZodError) {
      return { error: error.errors[0]?.message || "Validation failed" };
    }
    
    return { error: "An unexpected error occurred. Please try again." };
  }
}

export async function registerAction(
  prevState: any,
  formData: FormData
): Promise<{ success?: boolean; error?: string; user?: User }> {
  try {
    // Validate form data
    const rawData = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      name: formData.get("name") as string,
    };

    const validatedData = RegisterSchema.parse(rawData);

    // TODO: Check if user already exists in database
    // Mock check for demonstration
    if (validatedData.email === "existing@example.com") {
      return { error: "An account with this email already exists" };
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(validatedData.password, 12);

    // TODO: Save user to database
    // Mock user creation
    const newUser = {
      id: `user-${Date.now()}`,
      email: validatedData.email,
      name: validatedData.name,
      hashedPassword,
    };

    // Create JWT
    const token = await createJWT({
      userId: newUser.id,
      email: newUser.email,
      name: newUser.name,
    });

    // Set secure cookie
    const cookieStore = await cookies();
    cookieStore.set("auth-token", token, COOKIE_OPTIONS);

    const user: User = {
      id: newUser.id,
      email: newUser.email,
      name: newUser.name,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    return { success: true, user };
  } catch (error) {
    console.error("Registration error:", error);
    
    if (error instanceof z.ZodError) {
      return { error: error.errors[0]?.message || "Validation failed" };
    }
    
    return { error: "An unexpected error occurred. Please try again." };
  }
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete("auth-token");
  redirect("/");
}

export async function resetPasswordAction(
  prevState: any,
  formData: FormData
): Promise<{ success?: boolean; error?: string; message?: string }> {
  try {
    // Validate form data
    const rawData = {
      email: formData.get("email") as string,
    };

    const validatedData = ResetPasswordSchema.parse(rawData);

    // TODO: Generate reset token and send email
    // Mock implementation
    console.log(`Password reset requested for: ${validatedData.email}`);

    return {
      success: true,
      message: "Password reset instructions have been sent to your email",
    };
  } catch (error) {
    console.error("Password reset error:", error);
    
    if (error instanceof z.ZodError) {
      return { error: error.errors[0]?.message || "Validation failed" };
    }
    
    return { error: "An unexpected error occurred. Please try again." };
  }
}

// Utility function to check authentication status for middleware
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session !== null;
}

// Function to refresh JWT token (for token rotation)
export async function refreshToken(): Promise<boolean> {
  try {
    const session = await getSession();
    
    if (!session) {
      return false;
    }

    // Check if token needs refresh (e.g., if it expires in less than 24 hours)
    const now = Math.floor(Date.now() / 1000);
    const timeUntilExpiry = session.exp - now;
    const shouldRefresh = timeUntilExpiry < 60 * 60 * 24; // 24 hours

    if (shouldRefresh) {
      const newToken = await createJWT({
        userId: session.userId,
        email: session.email,
        name: session.name,
      });

      const cookieStore = await cookies();
      cookieStore.set("auth-token", newToken, COOKIE_OPTIONS);
    }

    return true;
  } catch (error) {
    console.error("Token refresh failed:", error);
    return false;
  }
}