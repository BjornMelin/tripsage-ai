import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LoginCredentials, RegisterCredentials } from "@/stores/auth/auth-core";
import { useAuthCore } from "@/stores/auth/auth-core";
import { createMockUser, resetAuthSlices, setupAuthSliceTests } from "./_shared";

// Mock fetch for API calls
global.fetch = vi.fn();

setupAuthSliceTests();

describe("AuthCore", () => {
  beforeEach(() => {
    resetAuthSlices();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useAuthCore());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isLoggingIn).toBe(false);
      expect(result.current.isRegistering).toBe(false);
    });

    it("computed properties work correctly with empty state", () => {
      const { result } = renderHook(() => useAuthCore());

      expect(result.current.userDisplayName).toBe("");
    });
  });

  describe("Login", () => {
    it("successfully logs in with valid credentials", async () => {
      const mockUser = createMockUser({ email: "test@example.com" });
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ user: mockUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const credentials: LoginCredentials = {
        email: "test@example.com",
        password: "password123",
        rememberMe: true,
      };

      let loginResult: boolean | undefined;
      await act(async () => {
        loginResult = await result.current.login(credentials);
      });

      expect(loginResult).toBe(true);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user?.email).toBe("test@example.com");
      expect(result.current.isLoggingIn).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("handles login with missing email", async () => {
      const { result } = renderHook(() => useAuthCore());

      const credentials = {
        email: "",
        password: "password123",
      } as LoginCredentials;

      let loginResult: boolean | undefined;
      await act(async () => {
        loginResult = await result.current.login(credentials);
      });

      expect(loginResult).toBe(false);
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe("Email and password are required");
    });

    it("handles login API error", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ message: "Invalid credentials" }),
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const credentials: LoginCredentials = {
        email: "test@example.com",
        password: "wrongpassword",
      };

      let loginResult: boolean | undefined;
      await act(async () => {
        loginResult = await result.current.login(credentials);
      });

      expect(loginResult).toBe(false);
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.error).toBe("Invalid credentials");
    });
  });

  describe("Register", () => {
    it("successfully registers with valid credentials", async () => {
      const mockUser = createMockUser({
        email: "newuser@example.com",
        firstName: "John",
        isEmailVerified: false,
        lastName: "Doe",
      });
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ user: mockUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const credentials: RegisterCredentials = {
        acceptTerms: true,
        confirmPassword: "password123",
        email: "newuser@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "password123",
      };

      let registerResult: boolean | undefined;
      await act(async () => {
        registerResult = await result.current.register(credentials);
      });

      expect(registerResult).toBe(true);
      expect(result.current.user?.email).toBe("newuser@example.com");
      expect(result.current.user?.firstName).toBe("John");
      expect(result.current.user?.lastName).toBe("Doe");
      expect(result.current.user?.isEmailVerified).toBe(false);
      expect(result.current.isRegistering).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("handles registration with mismatched passwords", async () => {
      const { result } = renderHook(() => useAuthCore());

      const credentials: RegisterCredentials = {
        acceptTerms: true,
        confirmPassword: "differentpassword",
        email: "newuser@example.com",
        password: "password123",
      };

      let registerResult: boolean | undefined;
      await act(async () => {
        registerResult = await result.current.register(credentials);
      });

      expect(registerResult).toBe(false);
      expect(result.current.error).toBe("Passwords do not match");
    });

    it("handles registration without accepting terms", async () => {
      const { result } = renderHook(() => useAuthCore());

      const credentials: RegisterCredentials = {
        acceptTerms: false,
        confirmPassword: "password123",
        email: "newuser@example.com",
        password: "password123",
      };

      let registerResult: boolean | undefined;
      await act(async () => {
        registerResult = await result.current.register(credentials);
      });

      expect(registerResult).toBe(false);
      expect(result.current.error).toBe("You must accept the terms and conditions");
    });
  });

  describe("Logout", () => {
    it("successfully logs out and clears auth state", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      // Set up authenticated state
      act(() => {
        useAuthCore.setState({
          isAuthenticated: true,
          user: createMockUser(),
        });
      });

      expect(result.current.isAuthenticated).toBe(true);

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe("User Management", () => {
    beforeEach(() => {
      act(() => {
        useAuthCore.setState({
          isAuthenticated: true,
          user: createMockUser(),
        });
      });
    });

    it("successfully updates user information", async () => {
      const updatedUser = createMockUser({
        bio: "Updated bio",
        firstName: "UpdatedFirst",
        lastName: "UpdatedLast",
      });
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ user: updatedUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const updates = {
        bio: "Updated bio",
        firstName: "UpdatedFirst",
        lastName: "UpdatedLast",
      };

      let updateResult: boolean | undefined;
      await act(async () => {
        updateResult = await result.current.updateUser(updates);
      });

      expect(updateResult).toBe(true);
      expect(result.current.user?.firstName).toBe("UpdatedFirst");
      expect(result.current.user?.lastName).toBe("UpdatedLast");
      expect(result.current.user?.bio).toBe("Updated bio");
    });

    it("handles update user when not logged in", async () => {
      act(() => {
        useAuthCore.setState({ user: null });
      });

      const { result } = renderHook(() => useAuthCore());

      let updateResult: boolean | undefined;
      await act(async () => {
        updateResult = await result.current.updateUser({ firstName: "Test" });
      });

      expect(updateResult).toBe(false);
    });

    it("successfully updates user preferences", async () => {
      const updatedUser = createMockUser({
        preferences: {
          language: "es",
          notifications: {
            email: true,
            tripReminders: false,
          },
          theme: "dark",
        },
      });
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ preferences: updatedUser.preferences, user: updatedUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const preferences = {
        language: "es",
        notifications: {
          email: true,
          tripReminders: false,
        },
        theme: "dark" as const,
      };

      let updateResult: boolean | undefined;
      await act(async () => {
        updateResult = await result.current.updatePreferences(preferences);
      });

      expect(updateResult).toBe(true);
      expect(result.current.user?.preferences?.theme).toBe("dark");
      expect(result.current.user?.preferences?.language).toBe("es");
    });

    it("successfully updates security settings", async () => {
      const updatedUser = createMockUser({
        security: {
          lastPasswordChange: "2025-01-01T00:00:00Z",
          twoFactorEnabled: true,
        },
      });
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ security: updatedUser.security, user: updatedUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      const security = {
        lastPasswordChange: "2025-01-01T00:00:00Z",
        twoFactorEnabled: true,
      };

      let updateResult: boolean | undefined;
      await act(async () => {
        updateResult = await result.current.updateSecurity(security);
      });

      expect(updateResult).toBe(true);
      expect(result.current.user?.security?.twoFactorEnabled).toBe(true);
      expect(result.current.user?.security?.lastPasswordChange).toBe(
        "2025-01-01T00:00:00Z"
      );
    });
  });

  describe("Utility Actions", () => {
    it("sets user directly", () => {
      const { result } = renderHook(() => useAuthCore());

      const user = createMockUser({ id: "user-1" });

      act(() => {
        result.current.setUser(user);
      });

      expect(result.current.user).toEqual(user);

      act(() => {
        result.current.setUser(null);
      });

      expect(result.current.user).toBeNull();
    });

    it("clears error", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        useAuthCore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it("initializes with valid session", async () => {
      const mockUser = createMockUser();
      vi.mocked(fetch).mockResolvedValueOnce({
        json: async () => ({ user: mockUser }),
        ok: true,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it("initializes with invalid session clears state", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
      } as Response);

      const { result } = renderHook(() => useAuthCore());

      await act(async () => {
        await result.current.initialize();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  describe("User Display Name", () => {
    it("uses displayName when available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(createMockUser({ displayName: "Custom Name" }));
      });

      expect(result.current.userDisplayName).toBe("Custom Name");
    });

    it("uses firstName + lastName when displayName not available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({ displayName: undefined, firstName: "John", lastName: "Doe" })
        );
      });

      expect(result.current.userDisplayName).toBe("John Doe");
    });

    it("uses firstName when lastName not available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({
            displayName: undefined,
            firstName: "Jane",
            lastName: undefined,
          })
        );
      });

      expect(result.current.userDisplayName).toBe("Jane");
    });

    it("uses email prefix when no names available", () => {
      const { result } = renderHook(() => useAuthCore());

      act(() => {
        result.current.setUser(
          createMockUser({
            displayName: undefined,
            email: "username@example.com",
            firstName: undefined,
            lastName: undefined,
          })
        );
      });

      expect(result.current.userDisplayName).toBe("username");
    });
  });
});
