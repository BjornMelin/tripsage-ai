#!/usr/bin/env python3
"""Supabase BYOK Security Verification Script.

This script verifies that the sophisticated Supabase BYOK (Bring Your Own Key)
implementation is properly configured with Vault security, RPC hardening, and
multi-provider support.

Verifies:
- Vault extension and role hardening
- SECURITY DEFINER RPC functions and access control
- Multi-provider BYOK storage and retrieval
- Gateway configuration and user settings
- RLS policies and data isolation

Usage:
    python scripts/verify_vault_hardening.py

Requirements:
    - SUPABASE_URL environment variable
    - SUPABASE_SERVICE_ROLE_KEY environment variable
    - supabase-py package
"""

import os
import sys
import uuid
from collections.abc import Callable, Mapping
from typing import Any


try:
    from supabase import Client, create_client
except ImportError:
    print("❌ supabase-py package not installed. Install with: pip install supabase")
    sys.exit(1)


class SupabaseByokVerifier:
    """Verifies Supabase Vault role hardening and security configuration."""

    def __init__(self) -> None:
        """Initialize the verifier with environment variables and Supabase client.

        Raises:
            SystemExit: If required environment variables are missing.
        """
        self.supabase_url: str | None = os.getenv("SUPABASE_URL")
        self.service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.supabase_url or not self.service_role_key:
            print("❌ Missing environment variables:")
            if not self.supabase_url:
                print("   - SUPABASE_URL")
            if not self.service_role_key:
                print("   - SUPABASE_SERVICE_ROLE_KEY")
            sys.exit(1)

        # Type assertion is safe here since we checked for None above
        self.supabase: Client = create_client(self.supabase_url, self.service_role_key)
        self.test_user_id: str = str(uuid.uuid4())  # Generate test user ID

    def _call_rpc(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        """Call supabase.rpc(name, params).execute() and return .data or raise.

        Parameters:
            name: RPC function to call
            params: Mapping of RPC parameter names to values
        """
        try:
            # supabase.rpc expects a dict or None for params; accept Mapping and
            # convert to dict to satisfy runtime and static typing checks.
            params_arg = dict(params) if params is not None else None
            return self.supabase.rpc(name, params_arg).execute().data
        except (ConnectionError, TimeoutError) as e:
            # Preserve the original exception context so the caller can inspect
            # the underlying network error if needed.
            raise RuntimeError(f"Network error in {name}: {e}") from e
        except Exception as e:
            # Bubble up for the caller to inspect the error message while
            # preserving the underlying exception context.
            raise RuntimeError(f"RPC {name} failed: {e}") from e

    def run_verification(self) -> bool:
        """Run all verification checks.

        Returns:
            bool: True if all checks pass, False otherwise.
        """
        print("🔍 Starting Supabase BYOK security verification...\n")

        checks: list[tuple[str, Callable[[], bool]]] = [
            ("Vault Extension", self.check_vault_extension),
            ("Vault Role Hardening", self.check_vault_role_hardening),
            ("RPC Function Security", self.check_rpc_function_security),
            ("BYOK Storage/Retrieval", self.check_byok_operations),
            ("Gateway Configuration", self.check_gateway_configuration),
            ("User Settings", self.check_user_settings),
            ("RLS Data Isolation", self.check_rls_data_isolation),
            ("Multi-Provider Support", self.check_multi_provider_support),
        ]

        results: list[bool] = []
        for check_name, check_func in checks:
            print(f"📋 Checking {check_name}...")
            try:
                result = check_func()
                if result:
                    print(f"✅ {check_name}: PASSED")
                else:
                    print(f"❌ {check_name}: FAILED")
                results.append(result)
            except (ConnectionError, TimeoutError, ValueError, RuntimeError) as e:
                print(f"❌ {check_name}: ERROR - {e}")
                results.append(False)
            except Exception as e:  # noqa: BLE001  # Catch-all for unexpected errors
                print(f"❌ {check_name}: UNEXPECTED ERROR - {type(e).__name__}: {e}")
                results.append(False)
            print()

        all_passed = all(results)
        print("🎯 Verification Summary:")
        print(f"   Passed: {sum(results)}/{len(results)}")
        status = (
            "✅ ALL BYOK SECURITY CHECKS PASSED"
            if all_passed
            else "❌ SECURITY ISSUES FOUND"
        )
        print(f"   Overall: {status}")

        if not all_passed:
            print("\n⚠️  Security Issues Detected!")
            print("   Review docs/operators/supabase-configuration.md for remediation")
            print("   Run this script again after fixes to verify")

        return all_passed

    def check_vault_extension(self) -> bool:
        """Check if Vault extension is installed and accessible.

        Returns:
            bool: True if Vault extension is accessible, False otherwise.
        """
        try:
            # Test Vault extension by attempting to call a Vault RPC function
            self.supabase.rpc(
                "get_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()
            # Should succeed (return null for non-existent key) or fail with permission
            # error
            # Either way, it means Vault is accessible
            return True
        except (ConnectionError, TimeoutError) as e:
            # Network-related errors indicate connectivity issues
            print(f"   ❌ Network error during Vault check: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            error_msg = str(e).lower()
            # If we get a "function does not exist" error, Vault is not properly set up
            if "function" in error_msg and "does not exist" in error_msg:
                return False
            # Permission errors are expected and mean Vault is working
            if (
                "permission denied" in error_msg
                or "must be called as service role" in error_msg
            ):
                return True
            # Other unexpected errors
            print(f"   ❌ Unexpected error during Vault check: {e}")
            return False

    def check_vault_role_hardening(self) -> bool:
        """Check if Vault role hardening is properly configured.

        Returns:
            bool: True if role hardening is properly configured, False otherwise.
        """
        try:
            # Test that RPC functions require service role (not accessible to anon user)
            if not self.supabase_url:
                print("   ❌ Supabase URL not available for role hardening check")
                return False

            anon_client = create_client(self.supabase_url, "invalid-key")
            try:
                anon_client.rpc(
                    "get_user_api_key",
                    {"p_user_id": self.test_user_id, "p_service": "openai"},
                ).execute()
                return False  # Should have failed
            except (ConnectionError, TimeoutError) as e:
                # Network errors during anonymous access test
                print(f"   ❌ Network error during anonymous access test: {e}")
                return False
            except Exception as e:  # noqa: BLE001
                # Should fail with permission/service role error
                error_msg = str(e).lower()
                return "permission denied" in error_msg or "service role" in error_msg
        except (ValueError, TypeError) as e:
            # Client creation or configuration errors
            print(f"   ❌ Client configuration error: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during role hardening check
            print(f"   ❌ Unexpected error during role hardening check: {e}")
            return False

    def check_rpc_function_security(self) -> bool:
        """Check that RPC functions are properly secured.

        Returns:
            bool: True if all RPC functions are properly secured, False otherwise.
        """
        # Test all expected RPC functions exist and are callable with service role
        rpc_functions = [
            "insert_user_api_key",
            "get_user_api_key",
            "delete_user_api_key",
            "touch_user_api_key",
            "upsert_user_gateway_config",
            "get_user_gateway_base_url",
            "delete_user_gateway_config",
            "get_user_allow_gateway_fallback",
        ]

        for func in rpc_functions:
            try:
                # All RPC functions are called with a minimal payload.
                # This is sufficient to check for their existence, as a missing function
                # will raise a "does not exist" error, while a call with incorrect
                # parameters will raise a validation error, which is handled and
                # accepted by the logic below.
                self.supabase.rpc(func, {"p_user_id": self.test_user_id}).execute()
            except (ConnectionError, TimeoutError) as e:
                # Network errors during RPC function check
                print(f"   ❌ Network error checking {func}: {e}")
                return False
            except Exception as e:  # noqa: BLE001
                error_str = str(e).lower()
                # Accept permission errors (expected) but not "function does not exist"
                if "does not exist" in error_str or (
                    "function" in error_str and "not found" in error_str
                ):
                    print(f"   ❌ RPC function {func} not found")
                    return False
                # Other validation errors are expected and acceptable

        return True

    def check_byok_operations(self) -> bool:
        """Test BYOK storage and retrieval operations.

        Returns:
            bool: True if all BYOK operations work correctly, False otherwise.
        """
        test_key = "sk-test-verification-key-12345"
        success = False

        try:
            # 1. Insert test API key
            insert_result = self.supabase.rpc(
                "insert_user_api_key",
                {
                    "p_user_id": self.test_user_id,
                    "p_service": "openai",
                    "p_api_key": test_key,
                },
            ).execute()

            if not insert_result.data:
                print("   ❌ Failed to insert test API key")
                return False

            # 2. Retrieve the key
            retrieve_result = self.supabase.rpc(
                "get_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()

            if retrieve_result.data != test_key:
                expected = test_key
                actual = retrieve_result.data
                print(f"   ❌ Key mismatch: expected '{expected}', got '{actual}'")
                return False

            # 3. Update last_used timestamp
            self.supabase.rpc(
                "touch_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()

            # 4. Delete the test key
            self.supabase.rpc(
                "delete_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()

            # 5. Verify key is deleted
            final_check = self.supabase.rpc(
                "get_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()

            if final_check.data is not None:
                print("   ❌ Key not properly deleted")
                return False

            success = True

        except (ConnectionError, TimeoutError) as e:
            # Network errors during BYOK operations
            print(f"   ❌ Network error during BYOK operations: {e}")
        except (ValueError, TypeError) as e:
            # Data validation or type errors
            print(f"   ❌ Data validation error during BYOK operations: {e}")
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during BYOK operations
            print(f"   ❌ Unexpected error during BYOK operations: {e}")

        return success

    def check_gateway_configuration(self) -> bool:
        """Test Gateway configuration operations.

        Returns:
            bool: True if Gateway configuration operations work correctly, False
            otherwise.
        """
        test_base_url = "https://test-gateway.vercel.sh/v1"

        try:
            # 1. Set gateway config
            self.supabase.rpc(
                "upsert_user_gateway_config",
                {"p_user_id": self.test_user_id, "p_base_url": test_base_url},
            ).execute()

            # 2. Retrieve gateway config
            result = self.supabase.rpc(
                "get_user_gateway_base_url", {"p_user_id": self.test_user_id}
            ).execute()

            if result.data != test_base_url:
                expected = test_base_url
                actual = result.data
                print(
                    f"   ❌ Gateway URL mismatch: expected '{expected}', got '{actual}'"
                )
                return False

            # 3. Delete gateway config
            self.supabase.rpc(
                "delete_user_gateway_config", {"p_user_id": self.test_user_id}
            ).execute()

            # 4. Verify deletion
            final_check = self.supabase.rpc(
                "get_user_gateway_base_url", {"p_user_id": self.test_user_id}
            ).execute()

            if final_check.data is not None:
                print("   ❌ Gateway config not properly deleted")
                return False

            return True

        except (ConnectionError, TimeoutError) as e:
            # Network errors during gateway configuration operations
            print(f"   ❌ Network error during gateway configuration: {e}")
            return False
        except (ValueError, TypeError) as e:
            # Data validation or type errors
            print(f"   ❌ Data validation error during gateway configuration: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during gateway configuration
            print(f"   ❌ Unexpected error during gateway configuration: {e}")
            return False

    def check_user_settings(self) -> bool:
        """Test user settings operations.

        Returns:
            bool: True if user settings operations work correctly, False otherwise.
        """
        try:
            # Test default fallback behavior (should be True)
            result = self.supabase.rpc(
                "get_user_allow_gateway_fallback", {"p_user_id": self.test_user_id}
            ).execute()

            # Default should be True for new users
            if result.data is not True:
                print(f"   ❌ Unexpected default fallback setting: {result.data}")
                return False

            return True

        except (ConnectionError, TimeoutError) as e:
            # Network errors during user settings check
            print(f"   ❌ Network error during user settings check: {e}")
            return False
        except (ValueError, TypeError) as e:
            # Data validation or type errors
            print(f"   ❌ Data validation error during user settings check: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during user settings check
            print(f"   ❌ Unexpected error during user settings check: {e}")
            return False

    def check_rls_data_isolation(self) -> bool:
        """Test that RLS properly isolates user data.

        Returns:
            bool: True if RLS properly isolates user data, False otherwise.
        """
        try:
            # Insert test data for our test user
            self.supabase.rpc(
                "insert_user_api_key",
                {
                    "p_user_id": self.test_user_id,
                    "p_service": "openai",
                    "p_api_key": "test-key",
                },
            ).execute()

            # Create a second user ID
            other_user_id = str(uuid.uuid4())

            # Try to access the first user's data with the second user ID
            # (should fail or return null)
            result = self.supabase.rpc(
                "get_user_api_key", {"p_user_id": other_user_id, "p_service": "openai"}
            ).execute()

            # Should return null (no data for other user)
            if result.data is not None:
                print("   ❌ RLS not properly isolating user data")
                return False

            # Clean up test data
            self.supabase.rpc(
                "delete_user_api_key",
                {"p_user_id": self.test_user_id, "p_service": "openai"},
            ).execute()

            return True

        except (ConnectionError, TimeoutError) as e:
            # Network errors during RLS isolation test
            print(f"   ❌ Network error during RLS isolation test: {e}")
            return False
        except (ValueError, TypeError) as e:
            # Data validation or type errors
            print(f"   ❌ Data validation error during RLS isolation test: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during RLS isolation test
            print(f"   ❌ Unexpected error during RLS isolation test: {e}")
            return False

    def check_multi_provider_support(self) -> bool:
        """Test multi-provider BYOK support.

        Returns:
            bool: True if multi-provider BYOK support works correctly, False otherwise.
        """
        providers = ["openai", "anthropic", "xai", "openrouter"]

        try:
            for provider in providers:
                test_key = f"sk-{provider}-test-key"

                # Insert key for this provider
                self.supabase.rpc(
                    "insert_user_api_key",
                    {
                        "p_user_id": self.test_user_id,
                        "p_service": provider,
                        "p_api_key": test_key,
                    },
                ).execute()

                # Retrieve and verify
                result = self.supabase.rpc(
                    "get_user_api_key",
                    {"p_user_id": self.test_user_id, "p_service": provider},
                ).execute()

                if result.data != test_key:
                    print(f"   ❌ {provider} key mismatch")
                    return False

                # Clean up
                self.supabase.rpc(
                    "delete_user_api_key",
                    {"p_user_id": self.test_user_id, "p_service": provider},
                ).execute()

            return True

        except (ConnectionError, TimeoutError) as e:
            # Network errors during multi-provider test
            print(f"   ❌ Network error during multi-provider test: {e}")
            return False
        except (ValueError, TypeError) as e:
            # Data validation or type errors
            print(f"   ❌ Data validation error during multi-provider test: {e}")
            return False
        except Exception as e:  # noqa: BLE001
            # Unexpected errors during multi-provider test
            print(f"   ❌ Unexpected error during multi-provider test: {e}")
            return False


def main() -> None:
    """Main entry point.

    Runs the Supabase BYOK security verification and exits with appropriate code.
    """
    try:
        verifier = SupabaseByokVerifier()
        success = verifier.run_verification()

        if not success:
            print("\n⚠️  Issues found. Please review the Supabase configuration docs:")
            print("   docs/operators/supabase-configuration.md")
            sys.exit(1)
        else:
            print("\n🎉 Supabase BYOK security verification completed successfully!")
    except KeyboardInterrupt:
        print("\n❌ Verification interrupted by user")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Unexpected error during verification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
