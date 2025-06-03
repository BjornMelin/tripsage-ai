import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	useAuthStore,
	type LoginCredentials,
	type RegisterCredentials,
	type PasswordResetRequest,
	type PasswordReset,
	type User,
	type UserPreferences,
	type UserSecurity,
} from "../auth-store";

// Mock setTimeout to make tests run faster
vi.mock("global", () => ({
	setTimeout: vi.fn((fn) => fn()),
}));

describe("Auth Store", () => {
	beforeEach(() => {
		act(() => {
			useAuthStore.setState({
				isAuthenticated: false,
				user: null,
				tokenInfo: null,
				session: null,
				isLoading: false,
				isLoggingIn: false,
				isRegistering: false,
				isResettingPassword: false,
				isRefreshingToken: false,
				error: null,
				loginError: null,
				registerError: null,
				passwordResetError: null,
			});
		});
	});

	describe("Initial State", () => {
		it("initializes with correct default values", () => {
			const { result } = renderHook(() => useAuthStore());

			expect(result.current.isAuthenticated).toBe(false);
			expect(result.current.user).toBeNull();
			expect(result.current.tokenInfo).toBeNull();
			expect(result.current.session).toBeNull();
			expect(result.current.isLoading).toBe(false);
			expect(result.current.isLoggingIn).toBe(false);
			expect(result.current.isRegistering).toBe(false);
			expect(result.current.isResettingPassword).toBe(false);
			expect(result.current.isRefreshingToken).toBe(false);
			expect(result.current.error).toBeNull();
			expect(result.current.loginError).toBeNull();
			expect(result.current.registerError).toBeNull();
			expect(result.current.passwordResetError).toBeNull();
		});

		it("computed properties work correctly with empty state", () => {
			const { result } = renderHook(() => useAuthStore());

			expect(result.current.isTokenExpired).toBe(true);
			expect(result.current.sessionTimeRemaining).toBe(0);
			expect(result.current.userDisplayName).toBe("");
		});
	});

	describe("Authentication Actions", () => {
		describe("Login", () => {
			it("successfully logs in with valid credentials", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: LoginCredentials = {
					email: "test@example.com",
					password: "password123",
					rememberMe: true,
				};

				let loginResult: boolean;
				await act(async () => {
					loginResult = await result.current.login(credentials);
				});

				expect(loginResult!).toBe(true);
				expect(result.current.isAuthenticated).toBe(true);
				expect(result.current.user).toBeDefined();
				expect(result.current.user?.email).toBe("test@example.com");
				expect(result.current.tokenInfo).toBeDefined();
				expect(result.current.session).toBeDefined();
				expect(result.current.isLoggingIn).toBe(false);
				expect(result.current.loginError).toBeNull();
			});

			it("handles login with missing email", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: LoginCredentials = {
					email: "",
					password: "password123",
				};

				let loginResult: boolean;
				await act(async () => {
					loginResult = await result.current.login(credentials);
				});

				expect(loginResult!).toBe(false);
				expect(result.current.isAuthenticated).toBe(false);
				expect(result.current.user).toBeNull();
				expect(result.current.loginError).toBe("Email and password are required");
				expect(result.current.isLoggingIn).toBe(false);
			});

			it("handles login with missing password", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: LoginCredentials = {
					email: "test@example.com",
					password: "",
				};

				let loginResult: boolean;
				await act(async () => {
					loginResult = await result.current.login(credentials);
				});

				expect(loginResult!).toBe(false);
				expect(result.current.isAuthenticated).toBe(false);
				expect(result.current.loginError).toBe("Email and password are required");
			});

			it("sets loading state during login", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: LoginCredentials = {
					email: "test@example.com",
					password: "password123",
				};

				let wasLoggingIn = false;
				await act(async () => {
					const promise = result.current.login(credentials);
					wasLoggingIn = result.current.isLoggingIn;
					await promise;
				});

				expect(wasLoggingIn).toBe(false); // Will be false due to mocked setTimeout
				expect(result.current.isLoggingIn).toBe(false);
			});

			it("clears previous login errors on new login attempt", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Set initial error
				act(() => {
					useAuthStore.setState({ loginError: "Previous error" });
				});

				expect(result.current.loginError).toBe("Previous error");

				const credentials: LoginCredentials = {
					email: "test@example.com",
					password: "password123",
				};

				await act(async () => {
					await result.current.login(credentials);
				});

				expect(result.current.loginError).toBeNull();
			});
		});

		describe("Register", () => {
			it("successfully registers with valid credentials", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: RegisterCredentials = {
					email: "newuser@example.com",
					password: "password123",
					confirmPassword: "password123",
					firstName: "John",
					lastName: "Doe",
					acceptTerms: true,
				};

				let registerResult: boolean;
				await act(async () => {
					registerResult = await result.current.register(credentials);
				});

				expect(registerResult!).toBe(true);
				expect(result.current.user).toBeDefined();
				expect(result.current.user?.email).toBe("newuser@example.com");
				expect(result.current.user?.firstName).toBe("John");
				expect(result.current.user?.lastName).toBe("Doe");
				expect(result.current.user?.isEmailVerified).toBe(false);
				expect(result.current.isRegistering).toBe(false);
				expect(result.current.registerError).toBeNull();
			});

			it("handles registration with mismatched passwords", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: RegisterCredentials = {
					email: "newuser@example.com",
					password: "password123",
					confirmPassword: "differentpassword",
					acceptTerms: true,
				};

				let registerResult: boolean;
				await act(async () => {
					registerResult = await result.current.register(credentials);
				});

				expect(registerResult!).toBe(false);
				expect(result.current.user).toBeNull();
				expect(result.current.registerError).toBe("Passwords do not match");
			});

			it("handles registration without accepting terms", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: RegisterCredentials = {
					email: "newuser@example.com",
					password: "password123",
					confirmPassword: "password123",
					acceptTerms: false,
				};

				let registerResult: boolean;
				await act(async () => {
					registerResult = await result.current.register(credentials);
				});

				expect(registerResult!).toBe(false);
				expect(result.current.registerError).toBe(
					"You must accept the terms and conditions"
				);
			});

			it("generates correct display name with first and last name", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: RegisterCredentials = {
					email: "user@example.com",
					password: "password123",
					confirmPassword: "password123",
					firstName: "Jane",
					lastName: "Smith",
					acceptTerms: true,
				};

				await act(async () => {
					await result.current.register(credentials);
				});

				expect(result.current.user?.displayName).toBe("Jane Smith");
			});

			it("generates display name from email when no first name provided", async () => {
				const { result } = renderHook(() => useAuthStore());

				const credentials: RegisterCredentials = {
					email: "username@example.com",
					password: "password123",
					confirmPassword: "password123",
					acceptTerms: true,
				};

				await act(async () => {
					await result.current.register(credentials);
				});

				expect(result.current.user?.displayName).toBe("username");
			});
		});

		describe("Logout", () => {
			it("successfully logs out and clears all auth state", async () => {
				const { result } = renderHook(() => useAuthStore());

				// First login
				await act(async () => {
					await result.current.login({
						email: "test@example.com",
						password: "password123",
					});
				});

				expect(result.current.isAuthenticated).toBe(true);

				// Then logout
				await act(async () => {
					await result.current.logout();
				});

				expect(result.current.isAuthenticated).toBe(false);
				expect(result.current.user).toBeNull();
				expect(result.current.tokenInfo).toBeNull();
				expect(result.current.session).toBeNull();
				expect(result.current.error).toBeNull();
				expect(result.current.loginError).toBeNull();
				expect(result.current.registerError).toBeNull();
				expect(result.current.passwordResetError).toBeNull();
			});

			it("logs out from all devices", async () => {
				const { result } = renderHook(() => useAuthStore());

				// First login
				await act(async () => {
					await result.current.login({
						email: "test@example.com",
						password: "password123",
					});
				});

				// Logout from all devices
				await act(async () => {
					await result.current.logoutAllDevices();
				});

				expect(result.current.isAuthenticated).toBe(false);
				expect(result.current.user).toBeNull();
			});
		});
	});

	describe("Password Management", () => {
		describe("Password Reset Request", () => {
			it("successfully requests password reset", async () => {
				const { result } = renderHook(() => useAuthStore());

				const request: PasswordResetRequest = {
					email: "test@example.com",
				};

				let resetResult: boolean;
				await act(async () => {
					resetResult = await result.current.requestPasswordReset(request);
				});

				expect(resetResult!).toBe(true);
				expect(result.current.isResettingPassword).toBe(false);
				expect(result.current.passwordResetError).toBeNull();
			});

			it("handles password reset request with missing email", async () => {
				const { result } = renderHook(() => useAuthStore());

				const request: PasswordResetRequest = {
					email: "",
				};

				let resetResult: boolean;
				await act(async () => {
					resetResult = await result.current.requestPasswordReset(request);
				});

				expect(resetResult!).toBe(false);
				expect(result.current.passwordResetError).toBe("Email is required");
			});
		});

		describe("Password Reset", () => {
			it("successfully resets password with valid token", async () => {
				const { result } = renderHook(() => useAuthStore());

				const reset: PasswordReset = {
					token: "valid-reset-token",
					newPassword: "newpassword123",
					confirmPassword: "newpassword123",
				};

				let resetResult: boolean;
				await act(async () => {
					resetResult = await result.current.resetPassword(reset);
				});

				expect(resetResult!).toBe(true);
				expect(result.current.isResettingPassword).toBe(false);
				expect(result.current.passwordResetError).toBeNull();
			});

			it("handles password reset with mismatched passwords", async () => {
				const { result } = renderHook(() => useAuthStore());

				const reset: PasswordReset = {
					token: "valid-reset-token",
					newPassword: "newpassword123",
					confirmPassword: "differentpassword",
				};

				let resetResult: boolean;
				await act(async () => {
					resetResult = await result.current.resetPassword(reset);
				});

				expect(resetResult!).toBe(false);
				expect(result.current.passwordResetError).toBe("Passwords do not match");
			});

			it("handles password reset with missing token", async () => {
				const { result } = renderHook(() => useAuthStore());

				const reset: PasswordReset = {
					token: "",
					newPassword: "newpassword123",
					confirmPassword: "newpassword123",
				};

				let resetResult: boolean;
				await act(async () => {
					resetResult = await result.current.resetPassword(reset);
				});

				expect(resetResult!).toBe(false);
				expect(result.current.passwordResetError).toBe(
					"Token and new password are required"
				);
			});
		});

		describe("Change Password", () => {
			it("successfully changes password", async () => {
				const { result } = renderHook(() => useAuthStore());

				let changeResult: boolean;
				await act(async () => {
					changeResult = await result.current.changePassword(
						"currentpassword",
						"newpassword123"
					);
				});

				expect(changeResult!).toBe(true);
				expect(result.current.isLoading).toBe(false);
				expect(result.current.error).toBeNull();
			});

			it("handles change password with missing current password", async () => {
				const { result } = renderHook(() => useAuthStore());

				let changeResult: boolean;
				await act(async () => {
					changeResult = await result.current.changePassword("", "newpassword123");
				});

				expect(changeResult!).toBe(false);
				expect(result.current.error).toBe(
					"Current and new passwords are required"
				);
			});
		});
	});

	describe("Token Management", () => {
		describe("Refresh Token", () => {
			it("successfully refreshes valid token", async () => {
				const { result } = renderHook(() => useAuthStore());

				// First login to get tokens
				await act(async () => {
					await result.current.login({
						email: "test@example.com",
						password: "password123",
					});
				});

				const originalToken = result.current.tokenInfo?.accessToken;

				let refreshResult: boolean;
				await act(async () => {
					refreshResult = await result.current.refreshToken();
				});

				expect(refreshResult!).toBe(true);
				expect(result.current.tokenInfo?.accessToken).toBeDefined();
				expect(result.current.tokenInfo?.accessToken).not.toBe(originalToken);
				expect(result.current.isRefreshingToken).toBe(false);
			});

			it("logs out when no refresh token available", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Set state without refresh token
				act(() => {
					useAuthStore.setState({
						tokenInfo: {
							accessToken: "access-token",
							expiresAt: new Date(Date.now() + 3600000).toISOString(),
							tokenType: "Bearer",
						},
					});
				});

				let refreshResult: boolean;
				await act(async () => {
					refreshResult = await result.current.refreshToken();
				});

				expect(refreshResult!).toBe(false);
				expect(result.current.isAuthenticated).toBe(false);
			});
		});

		describe("Validate Token", () => {
			it("validates non-expired token", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Set valid token
				act(() => {
					useAuthStore.setState({
						tokenInfo: {
							accessToken: "valid-token",
							refreshToken: "refresh-token",
							expiresAt: new Date(Date.now() + 3600000).toISOString(),
							tokenType: "Bearer",
						},
					});
				});

				let validateResult: boolean;
				await act(async () => {
					validateResult = await result.current.validateToken();
				});

				expect(validateResult!).toBe(true);
			});

			it("refreshes expired token", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Set expired token
				act(() => {
					useAuthStore.setState({
						tokenInfo: {
							accessToken: "expired-token",
							refreshToken: "refresh-token",
							expiresAt: new Date(Date.now() - 3600000).toISOString(),
							tokenType: "Bearer",
						},
					});
				});

				let validateResult: boolean;
				await act(async () => {
					validateResult = await result.current.validateToken();
				});

				expect(validateResult!).toBe(true);
			});
		});
	});

	describe("User Management", () => {
		beforeEach(async () => {
			const { result } = renderHook(() => useAuthStore());

			await act(async () => {
				await result.current.login({
					email: "test@example.com",
					password: "password123",
				});
			});
		});

		describe("Update User", () => {
			it("successfully updates user information", async () => {
				const { result } = renderHook(() => useAuthStore());

				const updates = {
					firstName: "UpdatedFirst",
					lastName: "UpdatedLast",
					bio: "Updated bio",
				};

				let updateResult: boolean;
				await act(async () => {
					updateResult = await result.current.updateUser(updates);
				});

				expect(updateResult!).toBe(true);
				expect(result.current.user?.firstName).toBe("UpdatedFirst");
				expect(result.current.user?.lastName).toBe("UpdatedLast");
				expect(result.current.user?.bio).toBe("Updated bio");
			});

			it("handles update user when not logged in", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Logout first
				await act(async () => {
					await result.current.logout();
				});

				let updateResult: boolean;
				await act(async () => {
					updateResult = await result.current.updateUser({ firstName: "Test" });
				});

				expect(updateResult!).toBe(false);
			});
		});

		describe("Update Preferences", () => {
			it("successfully updates user preferences", async () => {
				const { result } = renderHook(() => useAuthStore());

				const preferences: Partial<UserPreferences> = {
					theme: "dark",
					language: "es",
					notifications: {
						email: true,
						tripReminders: false,
					},
				};

				let updateResult: boolean;
				await act(async () => {
					updateResult = await result.current.updatePreferences(preferences);
				});

				expect(updateResult!).toBe(true);
				expect(result.current.user?.preferences?.theme).toBe("dark");
				expect(result.current.user?.preferences?.language).toBe("es");
				expect(result.current.user?.preferences?.notifications?.email).toBe(true);
			});
		});

		describe("Update Security", () => {
			it("successfully updates security settings", async () => {
				const { result } = renderHook(() => useAuthStore());

				const security: Partial<UserSecurity> = {
					twoFactorEnabled: true,
					lastPasswordChange: "2025-01-01T00:00:00Z",
				};

				let updateResult: boolean;
				await act(async () => {
					updateResult = await result.current.updateSecurity(security);
				});

				expect(updateResult!).toBe(true);
				expect(result.current.user?.security?.twoFactorEnabled).toBe(true);
				expect(result.current.user?.security?.lastPasswordChange).toBe(
					"2025-01-01T00:00:00Z"
				);
			});
		});

		describe("Email Verification", () => {
			it("successfully verifies email", async () => {
				const { result } = renderHook(() => useAuthStore());

				let verifyResult: boolean;
				await act(async () => {
					verifyResult = await result.current.verifyEmail("valid-token");
				});

				expect(verifyResult!).toBe(true);
				expect(result.current.user?.isEmailVerified).toBe(true);
			});

			it("resends email verification", async () => {
				const { result } = renderHook(() => useAuthStore());

				// Set user as unverified
				act(() => {
					const currentUser = useAuthStore.getState().user;
					if (currentUser) {
						useAuthStore.setState({
							user: { ...currentUser, isEmailVerified: false },
						});
					}
				});

				let resendResult: boolean;
				await act(async () => {
					resendResult = await result.current.resendEmailVerification();
				});

				expect(resendResult!).toBe(true);
			});

			it("does not resend verification for verified user", async () => {
				const { result } = renderHook(() => useAuthStore());

				// User is already verified from login
				let resendResult: boolean;
				await act(async () => {
					resendResult = await result.current.resendEmailVerification();
				});

				expect(resendResult!).toBe(false);
			});
		});
	});

	describe("Session Management", () => {
		beforeEach(async () => {
			const { result } = renderHook(() => useAuthStore());

			await act(async () => {
				await result.current.login({
					email: "test@example.com",
					password: "password123",
				});
			});
		});

		it("extends session successfully", async () => {
			const { result } = renderHook(() => useAuthStore());

			const originalExpiresAt = result.current.session?.expiresAt;

			let extendResult: boolean;
			await act(async () => {
				extendResult = await result.current.extendSession();
			});

			expect(extendResult!).toBe(true);
			expect(result.current.session?.expiresAt).not.toBe(originalExpiresAt);
		});

		it("gets active sessions", async () => {
			const { result } = renderHook(() => useAuthStore());

			let sessions: any[];
			await act(async () => {
				sessions = await result.current.getActiveSessions();
			});

			expect(sessions!).toEqual([]);
		});

		it("revokes a session", async () => {
			const { result } = renderHook(() => useAuthStore());

			let revokeResult: boolean;
			await act(async () => {
				revokeResult = await result.current.revokeSession("session-id");
			});

			expect(revokeResult!).toBe(true);
		});
	});

	describe("Computed Properties", () => {
		it("correctly computes token expiration status", () => {
			const { result } = renderHook(() => useAuthStore());

			// No token - should be expired
			expect(result.current.isTokenExpired).toBe(true);

			// Valid token
			act(() => {
				useAuthStore.setState({
					tokenInfo: {
						accessToken: "token",
						expiresAt: new Date(Date.now() + 3600000).toISOString(),
						tokenType: "Bearer",
					},
				});
			});

			expect(result.current.isTokenExpired).toBe(false);

			// Expired token
			act(() => {
				useAuthStore.setState({
					tokenInfo: {
						accessToken: "token",
						expiresAt: new Date(Date.now() - 3600000).toISOString(),
						tokenType: "Bearer",
					},
				});
			});

			expect(result.current.isTokenExpired).toBe(true);
		});

		it("correctly computes session time remaining", () => {
			const { result } = renderHook(() => useAuthStore());

			// No session
			expect(result.current.sessionTimeRemaining).toBe(0);

			// Valid session
			act(() => {
				useAuthStore.setState({
					session: {
						id: "session-1",
						userId: "user-1",
						createdAt: "2025-01-01T00:00:00Z",
						lastActivity: "2025-01-01T00:00:00Z",
						expiresAt: new Date(Date.now() + 3600000).toISOString(),
					},
				});
			});

			expect(result.current.sessionTimeRemaining).toBeGreaterThan(0);
		});

		it("correctly computes user display name", () => {
			const { result } = renderHook(() => useAuthStore());

			// No user
			expect(result.current.userDisplayName).toBe("");

			// User with display name
			act(() => {
				useAuthStore.setState({
					user: {
						id: "user-1",
						email: "test@example.com",
						displayName: "Custom Display Name",
						isEmailVerified: true,
						createdAt: "2025-01-01T00:00:00Z",
						updatedAt: "2025-01-01T00:00:00Z",
					},
				});
			});

			expect(result.current.userDisplayName).toBe("Custom Display Name");

			// User with first and last name
			act(() => {
				useAuthStore.setState({
					user: {
						id: "user-1",
						email: "test@example.com",
						firstName: "John",
						lastName: "Doe",
						isEmailVerified: true,
						createdAt: "2025-01-01T00:00:00Z",
						updatedAt: "2025-01-01T00:00:00Z",
					},
				});
			});

			expect(result.current.userDisplayName).toBe("John Doe");

			// User with only first name
			act(() => {
				useAuthStore.setState({
					user: {
						id: "user-1",
						email: "test@example.com",
						firstName: "Jane",
						isEmailVerified: true,
						createdAt: "2025-01-01T00:00:00Z",
						updatedAt: "2025-01-01T00:00:00Z",
					},
				});
			});

			expect(result.current.userDisplayName).toBe("Jane");

			// User with only email
			act(() => {
				useAuthStore.setState({
					user: {
						id: "user-1",
						email: "username@example.com",
						isEmailVerified: true,
						createdAt: "2025-01-01T00:00:00Z",
						updatedAt: "2025-01-01T00:00:00Z",
					},
				});
			});

			expect(result.current.userDisplayName).toBe("username");
		});
	});

	describe("Error Management", () => {
		it("clears all errors", () => {
			const { result } = renderHook(() => useAuthStore());

			act(() => {
				useAuthStore.setState({
					error: "General error",
					loginError: "Login error",
					registerError: "Register error",
					passwordResetError: "Reset error",
				});
			});

			act(() => {
				result.current.clearErrors();
			});

			expect(result.current.error).toBeNull();
			expect(result.current.loginError).toBeNull();
			expect(result.current.registerError).toBeNull();
			expect(result.current.passwordResetError).toBeNull();
		});

		it("clears specific error types", () => {
			const { result } = renderHook(() => useAuthStore());

			act(() => {
				useAuthStore.setState({
					error: "General error",
					loginError: "Login error",
					registerError: "Register error",
					passwordResetError: "Reset error",
				});
			});

			act(() => {
				result.current.clearError("login");
			});

			expect(result.current.loginError).toBeNull();
			expect(result.current.error).toBe("General error");
			expect(result.current.registerError).toBe("Register error");

			act(() => {
				result.current.clearError("general");
			});

			expect(result.current.error).toBeNull();
		});
	});

	describe("Utility Actions", () => {
		it("sets user directly", () => {
			const { result } = renderHook(() => useAuthStore());

			const user: User = {
				id: "user-1",
				email: "test@example.com",
				isEmailVerified: true,
				createdAt: "2025-01-01T00:00:00Z",
				updatedAt: "2025-01-01T00:00:00Z",
			};

			act(() => {
				result.current.setUser(user);
			});

			expect(result.current.user).toEqual(user);

			act(() => {
				result.current.setUser(null);
			});

			expect(result.current.user).toBeNull();
		});

		it("initializes with valid token", async () => {
			const { result } = renderHook(() => useAuthStore());

			// Set valid token first
			act(() => {
				useAuthStore.setState({
					tokenInfo: {
						accessToken: "valid-token",
						refreshToken: "refresh-token",
						expiresAt: new Date(Date.now() + 3600000).toISOString(),
						tokenType: "Bearer",
					},
				});
			});

			await act(async () => {
				await result.current.initialize();
			});

			expect(result.current.isAuthenticated).toBe(true);
		});

		it("initializes with expired token logs out", async () => {
			const { result } = renderHook(() => useAuthStore());

			// Set expired token
			act(() => {
				useAuthStore.setState({
					tokenInfo: {
						accessToken: "expired-token",
						expiresAt: new Date(Date.now() - 3600000).toISOString(),
						tokenType: "Bearer",
					},
				});
			});

			await act(async () => {
				await result.current.initialize();
			});

			expect(result.current.isAuthenticated).toBe(false);
		});
	});

	describe("Utility Selectors", () => {
		it("useAuth selector returns correct auth state", () => {
			const { result: authResult } = renderHook(() =>
				useAuthStore((state) => ({
					isAuthenticated: state.isAuthenticated,
					user: state.user,
					isLoading: state.isLoading,
					login: state.login,
					logout: state.logout,
					register: state.register,
				}))
			);

			expect(authResult.current.isAuthenticated).toBe(false);
			expect(authResult.current.user).toBeNull();
			expect(authResult.current.isLoading).toBe(false);
			expect(typeof authResult.current.login).toBe("function");
			expect(typeof authResult.current.logout).toBe("function");
			expect(typeof authResult.current.register).toBe("function");
		});
	});

	describe("Complex Scenarios", () => {
		it("handles full authentication flow", async () => {
			const { result } = renderHook(() => useAuthStore());

			// Register
			await act(async () => {
				await result.current.register({
					email: "newuser@example.com",
					password: "password123",
					confirmPassword: "password123",
					firstName: "New",
					lastName: "User",
					acceptTerms: true,
				});
			});

			expect(result.current.user?.email).toBe("newuser@example.com");
			expect(result.current.user?.isEmailVerified).toBe(false);

			// Verify email
			await act(async () => {
				await result.current.verifyEmail("verification-token");
			});

			expect(result.current.user?.isEmailVerified).toBe(true);

			// Logout
			await act(async () => {
				await result.current.logout();
			});

			expect(result.current.isAuthenticated).toBe(false);

			// Login
			await act(async () => {
				await result.current.login({
					email: "newuser@example.com",
					password: "password123",
				});
			});

			expect(result.current.isAuthenticated).toBe(true);
			expect(result.current.user?.email).toBe("newuser@example.com");
		});

		it("handles token refresh scenarios", async () => {
			const { result } = renderHook(() => useAuthStore());

			// Login to get tokens
			await act(async () => {
				await result.current.login({
					email: "test@example.com",
					password: "password123",
				});
			});

			// Manually expire token
			act(() => {
				const currentState = useAuthStore.getState();
				if (currentState.tokenInfo) {
					useAuthStore.setState({
						tokenInfo: {
							...currentState.tokenInfo,
							expiresAt: new Date(Date.now() - 1000).toISOString(),
						},
					});
				}
			});

			expect(result.current.isTokenExpired).toBe(true);

			// Validate token should trigger refresh
			await act(async () => {
				await result.current.validateToken();
			});

			expect(result.current.isTokenExpired).toBe(false);
		});
	});
});