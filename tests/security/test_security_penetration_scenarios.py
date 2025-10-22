"""Security penetration test scenarios for API key validation infrastructure.

This module provides penetration testing scenarios covering
realistic attack vectors against the API key validation system. Tests
simulate real-world attack patterns including advanced persistent threats,
multi-vector attacks, and sophisticated bypass attempts.

Based on OWASP WSTG methodology and real-world penetration testing practices.
"""

import asyncio
import base64
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from tripsage.api.middlewares.authentication import (
    AuthenticationMiddleware,
)


@pytest.fixture
def mock_services():
    """Mock all required services for APT testing."""
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_settings = Mock()
    mock_secret_key = Mock()
    mock_secret_key.get_secret_value.return_value = "apt_test_master_secret_key"
    mock_settings.secret_key = mock_secret_key
    mock_jwt_secret = Mock()
    mock_jwt_secret.get_secret_value.return_value = "jwt_secret"
    mock_settings.database_jwt_secret = mock_jwt_secret

    return {"db": mock_db, "cache": mock_cache, "settings": mock_settings}


@pytest.fixture
def penetration_test_app(mock_services) -> FastAPI:
    """FastAPI application configured for penetration testing."""
    app = FastAPI()

    @app.get("/api/sensitive/data")
    async def sensitive_endpoint(request: Request):
        principal = getattr(request.state, "principal", None)
        if not principal:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Simulate sensitive data access
        return {
            "user_id": principal.id,
            "sensitive_data": "confidential_information",
            "access_level": getattr(principal, "role", "user"),
        }

    @app.get("/api/admin/users")
    async def admin_endpoint(request: Request):
        principal = getattr(request.state, "principal", None)
        if not principal:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check admin privileges
        if getattr(principal, "role", "user") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        return {"users": ["admin", "user1", "user2"], "total": 3}

    @app.post("/api/keys/validate")
    async def key_validation_endpoint(request: Request):
        data = await request.json()
        # Simulate key validation with potential vulnerabilities
        return {"valid": True, "service": data.get("service", "unknown")}

    return app


@pytest.fixture
def pentesting_client(penetration_test_app, mock_services) -> TestClient:
    """Test client with full security middleware stack."""
    # Legacy rate limiting middleware removed; SlowAPI covers inbound limits
    from tripsage_core.services.business.api_key_service import ApiKeyService

    # Mock audit functions to avoid logging to protected paths
    async def mock_audit_security_event(*args, **kwargs):
        return None

    async def mock_audit_api_key(*args, **kwargs):
        return None

    async def mock_audit_authentication(*args, **kwargs):
        return None

    with (
        patch(
            "tripsage.api.middlewares.authentication.audit_security_event",
            mock_audit_security_event,
        ),
        patch(
            "tripsage.api.middlewares.authentication.audit_api_key",
            mock_audit_api_key,
        ),
        patch(
            "tripsage.api.middlewares.authentication.audit_authentication",
            mock_audit_authentication,
        ),
        patch(
            "tripsage_core.services.business.audit_logging_service.SecurityAuditLogger",
            new=lambda *args, **kwargs: type(
                "_DL", (), {"log": lambda *_a, **_k: None}
            )(),
        ),
        patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger",
            new=AsyncMock(
                return_value=type("_DL", (), {"log": lambda *_a, **_k: None})()
            ),
        ),
    ):
        # Mock the _ensure_services method to avoid database connections
        async def mock_ensure_services(self):
            if not self._services_initialized:
                if self.key_service is None:
                    self.key_service = ApiKeyService(
                        db=mock_services["db"],
                        cache=mock_services["cache"],
                        settings=mock_services["settings"],
                    )
                self._services_initialized = True

        # Add authentication middleware with mocked _ensure_services
        auth_middleware = AuthenticationMiddleware(penetration_test_app)
        auth_middleware._ensure_services = mock_ensure_services.__get__(
            auth_middleware, AuthenticationMiddleware
        )

        penetration_test_app.add_middleware(
            type(auth_middleware).__bases__[0], dispatch=auth_middleware.dispatch
        )

        # Install SlowAPI rate limiting for penetration testing
        from tripsage.api.limiting import install_rate_limiting

        install_rate_limiting(penetration_test_app)

        return TestClient(penetration_test_app)


class TestPersistentThreatScenarios:
    """Penetration tests simulating Persistent Threat (APT) attack patterns."""

    async def test_apt_reconnaissance_phase(self, pentesting_client):
        """Test APT reconnaissance phase - information gathering."""
        reconnaissance_targets = [
            # Information disclosure endpoints
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
            "/api/.well-known/security.txt",
            "/robots.txt",
            "/sitemap.xml",
            # Common sensitive paths
            "/api/config",
            "/api/status",
            "/api/version",
            "/api/debug",
            "/api/metrics",
            "/api/admin",
            "/api/internal",
            # Hidden endpoints
            "/api/test",
            "/api/dev",
            "/api/staging",
            "/api/backup",
        ]

        gathered_info = {}

        for target in reconnaissance_targets:
            response = pentesting_client.get(target)
            gathered_info[target] = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_length": len(response.content),
                "response_time": response.elapsed.total_seconds()
                if hasattr(response, "elapsed")
                else 0,
            }

            # Analyze response for information disclosure
            if response.status_code == 200:
                content = response.text.lower()
                sensitive_disclosures = [
                    "version",
                    "debug",
                    "internal",
                    "secret",
                    "key",
                    "password",
                    "token",
                    "config",
                    "database",
                    "admin",
                ]

                for disclosure in sensitive_disclosures:
                    if disclosure in content:
                        gathered_info[target]["potential_disclosure"] = disclosure

        # APT would analyze this information to plan next phase
        _accessible_endpoints = [
            target
            for target, info in gathered_info.items()
            if info["status_code"] == 200
        ]

        # Should not expose sensitive internal information
        sensitive_exposures = [
            target
            for target, info in gathered_info.items()
            if "potential_disclosure" in info
        ]

        assert len(sensitive_exposures) == 0, (
            f"Sensitive information exposed: {sensitive_exposures}"
        )

    async def test_apt_initial_access_attempts(self, pentesting_client):
        """Test APT initial access phase - credential attacks."""
        # Simulate credential stuffing attack
        common_credentials = [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "123456"),
            ("administrator", "admin"),
            ("root", "root"),
            ("test", "test"),
            ("guest", "guest"),
            ("demo", "demo"),
        ]

        # Simulate brute force on authentication endpoints
        for username, password in common_credentials:
            # Test basic auth
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

            response = pentesting_client.get(
                "/api/sensitive/data", headers={"Authorization": f"Basic {credentials}"}
            )

            # Should not accept weak credentials
            assert response.status_code == 401

        # Test token-based attacks
        predictable_tokens = [
            "token",
            "123456",
            "admin_token",
            "Bearer admin",
            "guest_access",
            "test_token_123",
        ]

        for token in predictable_tokens:
            response = pentesting_client.get(
                "/api/sensitive/data", headers={"Authorization": f"Bearer {token}"}
            )

            # Should not accept predictable tokens
            assert response.status_code == 401

    async def test_apt_privilege_escalation_attempts(self, pentesting_client):
        """Test APT privilege escalation techniques."""
        # Create a low-privilege token
        import jwt

        low_privilege_payload = {
            "sub": "user_123",
            "email": "user@example.com",
            "role": "user",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }

        # Use weak secret for testing (in real test, would try to crack)
        weak_secret = "weak_secret_123"

        with patch("tripsage.api.core.config.get_settings") as mock_settings:
            mock_return = (
                mock_settings.return_value.database_jwt_secret.get_secret_value
            )
            mock_return.return_value = weak_secret

            _user_token = jwt.encode(
                low_privilege_payload, weak_secret, algorithm="HS256"
            )

            # Test privilege escalation attempts
            escalation_attempts = [
                # Role manipulation
                {**low_privilege_payload, "role": "admin"},
                {**low_privilege_payload, "role": "superuser"},
                {**low_privilege_payload, "admin": True},
                {**low_privilege_payload, "is_admin": True},
                {**low_privilege_payload, "permissions": ["admin", "write", "delete"]},
                # ID manipulation
                {**low_privilege_payload, "sub": "admin"},
                {**low_privilege_payload, "sub": "1"},  # Try to become user ID 1
                {**low_privilege_payload, "user_id": "admin"},
                # Scope/audience manipulation
                {**low_privilege_payload, "aud": "admin"},
                {**low_privilege_payload, "scope": "admin:write"},
                {**low_privilege_payload, "scopes": ["admin", "write", "delete"]},
            ]

            for malicious_payload in escalation_attempts:
                escalated_token = jwt.encode(
                    malicious_payload, weak_secret, algorithm="HS256"
                )

                response = pentesting_client.get(
                    "/api/admin/users",
                    headers={"Authorization": f"Bearer {escalated_token}"},
                )

                # Should not grant admin access through token manipulation
                assert response.status_code in [401, 403], (
                    f"Privilege escalation succeeded with payload: {malicious_payload}"
                )

    async def test_apt_lateral_movement_simulation(self, pentesting_client):
        """Test APT lateral movement techniques."""
        # Simulate compromised user trying to access other users' data
        _base_user_id = "user_123"

        # Target user IDs for lateral movement
        target_users = [
            "admin",
            "user_456",
            "service_account",
            "backup_user",
            "monitoring_user",
            "../admin",  # Path traversal attempt
            "user_123/../admin",  # Relative path injection
        ]

        for target_user in target_users:
            # Test direct user ID manipulation
            response = pentesting_client.get(
                f"/api/users/{target_user}/data", headers={"X-User-ID": target_user}
            )

            # Test via query parameters
            response = pentesting_client.get(
                "/api/sensitive/data",
                params={"user_id": target_user, "target_user": target_user},
            )

            # Test via headers
            response = pentesting_client.get(
                "/api/sensitive/data",
                headers={
                    "X-Target-User": target_user,
                    "X-Impersonate": target_user,
                    "X-On-Behalf-Of": target_user,
                },
            )

            # Should not allow unauthorized access to other users
            assert response.status_code in [401, 403, 404]

    async def test_apt_data_exfiltration_prevention(self, pentesting_client):
        """Test prevention of APT data exfiltration techniques."""
        # Simulate various data exfiltration attempts
        exfiltration_techniques = [
            # Bulk data requests
            {"endpoint": "/api/sensitive/data", "params": {"limit": 999999}},
            {"endpoint": "/api/sensitive/data", "params": {"page_size": 100000}},
            # Time-based data extraction
            {"endpoint": "/api/sensitive/data", "params": {"since": "1970-01-01"}},
            {"endpoint": "/api/sensitive/data", "params": {"until": "2030-12-31"}},
            # Format manipulation for data extraction
            {"endpoint": "/api/sensitive/data", "params": {"format": "csv"}},
            {"endpoint": "/api/sensitive/data", "params": {"export": "true"}},
            {"endpoint": "/api/sensitive/data", "params": {"download": "all"}},
            # Database query manipulation
            {
                "endpoint": "/api/sensitive/data",
                "params": {"query": "SELECT * FROM users"},
            },
            {"endpoint": "/api/sensitive/data", "params": {"filter": "1=1"}},
        ]

        for technique in exfiltration_techniques:
            response = pentesting_client.get(
                technique["endpoint"], params=technique.get("params", {})
            )

            # Should not allow bulk data exfiltration
            assert response.status_code in [401, 403, 400, 422]

            # Response should not contain large amounts of data
            if response.status_code == 200:
                content_length = len(response.content)
                assert content_length < 10000, (
                    f"Potential data exfiltration: {content_length} bytes"
                )

    async def test_apt_persistence_mechanism_detection(self, pentesting_client):
        """Test detection of APT persistence mechanisms."""
        # Test attempts to create persistence mechanisms
        persistence_attempts = [
            # Backdoor user creation
            {"username": "..admin", "role": "admin"},
            {"username": "admin.", "role": "admin"},
            {"username": "service_admin", "role": "service"},
            {"username": ".hidden_admin", "role": "admin"},
            # Scheduled task/cron job simulation
            {"task": "cleanup", "schedule": "* * * * *", "command": "rm -rf /"},
            {"task": "backup", "schedule": "@reboot", "command": "/tmp/backdoor"},
            # Configuration modification attempts
            {"config_key": "admin_users", "config_value": "attacker@evil.com"},
            {"config_key": "auth_bypass", "config_value": "true"},
            {"config_key": "debug_mode", "config_value": "enabled"},
        ]

        for attempt in persistence_attempts:
            # Test via POST requests
            response = pentesting_client.post("/api/admin/users", json=attempt)

            # Should not allow unauthorized persistence mechanisms
            assert response.status_code in [401, 403, 405, 422]

            # Test via PUT requests
            response = pentesting_client.put("/api/config", json=attempt)

            assert response.status_code in [401, 403, 405, 422]


class TestMultiVectorAttackScenarios:
    """Penetration tests for sophisticated multi-vector attack scenarios."""

    @pytest.fixture
    def attack_simulation_setup(self):
        """Setup for multi-vector attack simulation."""
        return {
            "attack_vectors": [],
            "compromised_endpoints": [],
            "gathered_intelligence": {},
            "persistence_attempts": [],
            "exfiltration_attempts": [],
        }

    async def test_coordinated_dos_and_credential_attack(
        self, pentesting_client, attack_simulation_setup
    ):
        """Test coordinated DoS and credential stuffing attack."""
        import threading

        # Phase 1: DoS to mask credential attack
        def dos_attack():
            """Simulate DoS attack component."""
            for _ in range(50):
                try:
                    pentesting_client.get("/api/sensitive/data")
                    time.sleep(0.01)
                except (HTTPException, ConnectionError, RuntimeError):
                    pass

        def credential_attack():
            """Simulate credential stuffing during DoS."""
            credentials = [
                "admin:admin123",
                "root:password",
                "user:user123",
                "test:test123",
            ]

            for cred in credentials:
                try:
                    username, password = cred.split(":")
                    encoded = base64.b64encode(
                        f"{username}:{password}".encode()
                    ).decode()
                    response = pentesting_client.get(
                        "/api/admin/users",
                        headers={"Authorization": f"Basic {encoded}"},
                    )
                    attack_simulation_setup["attack_vectors"].append(
                        {
                            "type": "credential_stuffing",
                            "credentials": cred,
                            "status": response.status_code,
                        }
                    )
                    time.sleep(0.1)
                except (HTTPException, ConnectionError, RuntimeError):
                    pass

        # Launch coordinated attack
        dos_thread = threading.Thread(target=dos_attack)
        cred_thread = threading.Thread(target=credential_attack)

        dos_thread.start()
        time.sleep(0.05)  # Slight delay to start DoS first
        cred_thread.start()

        dos_thread.join()
        cred_thread.join()

        # Verify defense effectiveness
        successful_auths = [
            attack
            for attack in attack_simulation_setup["attack_vectors"]
            if attack["status"] == 200
        ]

        assert len(successful_auths) == 0, "Credential attack succeeded during DoS"

    async def test_injection_chain_exploitation(self, pentesting_client):
        """Test chained injection attacks across multiple vectors."""
        # Test injection chain: XSS -> CSRF -> SQL -> Command
        injection_payloads = {
            "xss": [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "'><script>document.location='http://evil.com'</script>",
            ],
            "sql": [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT password FROM admin_users --",
            ],
            "nosql": [
                "{'$ne': null}",
                "{'$gt': ''}",
                "{'$where': 'this.username == this.password'}",
            ],
            "command": [
                "; cat /etc/passwd",
                "| whoami",
                "&& rm -rf /",
                "`id`",
            ],
            "ldap": [
                "*)(uid=*))(|(uid=*",
                "*)(|(password=*))",
                "admin)(&(password=*)))",
            ],
        }

        # Test each injection type across different input vectors
        input_vectors = [
            "query_params",
            "json_body",
            "headers",
            "form_data",
            "path_params",
        ]

        for injection_type, payloads in injection_payloads.items():
            for payload in payloads:
                for vector in input_vectors:
                    # Test query parameters
                    if vector == "query_params":
                        response = pentesting_client.get(
                            "/api/sensitive/data",
                            params={"search": payload, "filter": payload},
                        )

                    # Test JSON body
                    elif vector == "json_body":
                        response = pentesting_client.post(
                            "/api/keys/validate",
                            json={"service": payload, "key": payload},
                        )

                    # Test headers
                    elif vector == "headers":
                        response = pentesting_client.get(
                            "/api/sensitive/data",
                            headers={"X-Search": payload, "User-Agent": payload},
                        )

                    # Should not be vulnerable to any injection type
                    assert response.status_code in [400, 401, 403, 422], (
                        f"Potential {injection_type} injection via {vector}"
                    )

                    # Response should not contain injection artifacts
                    if response.status_code == 200:
                        content = response.text.lower()
                        injection_indicators = [
                            "error",
                            "exception",
                            "mysql",
                            "postgresql",
                            "sqlite",
                            "syntax",
                            "unexpected",
                            "undefined",
                            "null",
                        ]

                        for indicator in injection_indicators:
                            assert indicator not in content, (
                                f"Injection indicator '{indicator}' found in response"
                            )

    async def test_business_logic_attack_chains(self, pentesting_client):
        """Test business logic vulnerabilities in attack chains."""
        # Simulate complex business logic attacks
        business_logic_attacks = [
            # Race condition exploitation
            {
                "name": "concurrent_key_validation",
                "description": "Exploit race conditions in key validation",
                "attack": lambda: asyncio.gather(
                    *[
                        asyncio.create_task(
                            asyncio.to_thread(
                                pentesting_client.post,
                                "/api/keys/validate",
                                json={"service": "openai", "key": f"sk-test{i}"},
                            )
                        )
                        for i in range(10)
                    ]
                ),
            },
            # State manipulation
            {
                "name": "state_manipulation",
                "description": "Manipulate application state through timing",
                "attack": lambda: [
                    pentesting_client.get("/api/sensitive/data"),
                    pentesting_client.post(
                        "/api/keys/validate", json={"service": "test"}
                    ),
                    pentesting_client.get("/api/sensitive/data"),
                ],
            },
            # Workflow bypass
            {
                "name": "workflow_bypass",
                "description": "Bypass intended workflow sequences",
                "attack": lambda: [
                    pentesting_client.get("/api/admin/users"),  # Skip authentication
                    pentesting_client.post(
                        "/api/admin/users", json={"role": "admin"}
                    ),  # Direct admin creation
                    pentesting_client.delete("/api/admin/users/1"),  # Direct deletion
                ],
            },
        ]

        for attack_scenario in business_logic_attacks:
            try:
                if asyncio.iscoroutinefunction(attack_scenario["attack"]):
                    results = await attack_scenario["attack"]()
                else:
                    results = attack_scenario["attack"]()

                # Analyze results for business logic vulnerabilities
                if isinstance(results, list):
                    for result in results:
                        if hasattr(result, "status_code"):
                            # Should not allow unauthorized business operations
                            assert result.status_code in [401, 403, 405, 422], (
                                f"Business logic vulnerability in "
                                f"{attack_scenario['name']}"
                            )

            except (HTTPException, RuntimeError, ValueError) as e:
                # Attacks should fail gracefully
                assert (
                    "authentication" in str(e).lower()
                    or "authorization" in str(e).lower()
                )

    async def test_social_engineering_simulation(self, pentesting_client):
        """Test technical aspects of social engineering attacks."""
        # Simulate phishing/social engineering technical vectors
        social_engineering_vectors = [
            # Fake authentication pages
            {
                "endpoint": "/api/auth/fake_login",
                "method": "POST",
                "data": {"username": "admin", "password": "harvested_password"},
            },
            # Password reset abuse
            {
                "endpoint": "/api/auth/reset",
                "method": "POST",
                "data": {"email": "admin@company.com", "token": "predictable_token"},
            },
            # Support impersonation
            {
                "endpoint": "/api/support/access",
                "method": "POST",
                "data": {"support_code": "SUPPORT123", "user_id": "admin"},
            },
            # Emergency access
            {
                "endpoint": "/api/emergency/access",
                "method": "POST",
                "data": {"emergency_code": "EMERGENCY", "reason": "system_down"},
            },
        ]

        for vector in social_engineering_vectors:
            if vector["method"] == "POST":
                response = pentesting_client.post(
                    vector["endpoint"], json=vector["data"]
                )
            else:
                response = pentesting_client.get(
                    vector["endpoint"], params=vector["data"]
                )

            # Should not provide emergency/fake access mechanisms
            assert response.status_code in [401, 403, 404, 405], (
                f"Social engineering vector exposed: {vector['endpoint']}"
            )


class TestBypassTechniques:
    """Penetration tests for advanced security bypass techniques."""

    async def test_unicode_normalization_attacks(self, pentesting_client):
        """Test Unicode normalization bypass techniques."""
        # Unicode normalization attack vectors
        unicode_bypasses = [
            # Different Unicode representations of same characters
            ("admin", "admin"),  # Fullwidth characters (normalized)
            ("admin", "\u0430dmin"),  # Cyrillic `a` instead of `a`: admin
            ("admin", "\u03b1dmin"),  # Greek alpha instead of a: admin
            # Unicode homoglyphs
            ("admin", "\u0430d\u043c\u0438n"),  # Mixed Cyrillic: admin
            ("admin", "admin\u200b"),  # Zero-width space
            ("admin", "ad\u00admin"),  # Soft hyphen
            # Normalization forms
            ("caf\u00e9", "cafe\u0301"),  # NFC vs NFD normalization
            ("admin", "ad\u0300min"),  # Combining characters
        ]

        for _original, unicode_variant in unicode_bypasses:
            # Test in authentication
            response = pentesting_client.get(
                "/api/sensitive/data", headers={"X-Username": unicode_variant}
            )

            # Test in API key validation
            response = pentesting_client.post(
                "/api/keys/validate",
                json={"service": unicode_variant, "key": f"sk-{unicode_variant}"},
            )

            # Should not bypass security through Unicode normalization
            assert response.status_code in [400, 401, 403, 422]

    async def test_encoding_bypass_techniques(self, pentesting_client):
        """Test various encoding bypass techniques."""
        # Encoding bypass vectors
        encoding_bypasses = [
            # URL encoding
            ("admin", "admin", "%61%64%6d%69%6e"),
            ("'; DROP TABLE", "SQL injection", "%27%3b%20DROP%20TABLE"),
            # Double encoding
            ("admin", "admin", "%2561%2564%256d%2569%256e"),
            # HTML encoding
            ("admin", "admin", "&#97;&#100;&#109;&#105;&#110;"),
            ("<script>", "XSS", "&lt;script&gt;"),
            # Base64 encoding
            ("admin", "admin", base64.b64encode(b"admin").decode()),
            # Hex encoding
            ("admin", "admin", "61646d696e"),
            # Unicode encoding
            ("admin", "admin", "\\u0061\\u0064\\u006d\\u0069\\u006e"),
        ]

        for original, attack_type, encoded in encoding_bypasses:
            # Test in various input contexts
            contexts = [
                ("query", {"param": encoded}),
                ("header", {"X-Data": encoded}),
                ("json", {"field": encoded}),
            ]

            for context_type, context_data in contexts:
                if context_type == "query":
                    response = pentesting_client.get(
                        "/api/sensitive/data", params=context_data
                    )
                elif context_type == "header":
                    response = pentesting_client.get(
                        "/api/sensitive/data", headers=context_data
                    )
                elif context_type == "json":
                    response = pentesting_client.post(
                        "/api/keys/validate", json=context_data
                    )

                # Should not bypass validation through encoding
                if response.status_code == 200:
                    # Check if original malicious content appears in response
                    assert original not in response.text, (
                        f"Encoding bypass successful: {attack_type} via {context_type}"
                    )

    async def test_http_method_override_bypasses(self, pentesting_client):
        """Test HTTP method override bypass techniques."""
        # Method override techniques
        override_techniques = [
            ("X-HTTP-Method-Override", "DELETE"),
            ("X-Method-Override", "PUT"),
            ("_method", "PATCH"),
            ("X-HTTP-Method", "OPTIONS"),
        ]

        sensitive_endpoints = [
            "/api/admin/users",
            "/api/sensitive/data",
            "/api/keys/validate",
        ]

        for header_name, method in override_techniques:
            for endpoint in sensitive_endpoints:
                # Test method override via headers
                response = pentesting_client.post(
                    endpoint, headers={header_name: method}, json={"test": "data"}
                )

                # Should not allow method override bypass
                assert response.status_code in [401, 403, 405, 422]

                # Test method override via query parameters
                response = pentesting_client.post(
                    endpoint,
                    params={header_name.lower(): method},
                    json={"test": "data"},
                )

                assert response.status_code in [401, 403, 405, 422]

    async def test_content_type_confusion_attacks(self, pentesting_client):
        """Test content-type confusion bypass techniques."""
        # Content-type confusion vectors
        confusion_attacks = [
            # JSON in form data
            {
                "content_type": "application/x-www-form-urlencoded",
                "payload": '{"malicious": "payload"}',
                "expected_parsing": "form",
            },
            # XML in JSON
            {
                "content_type": "application/json",
                "payload": '<?xml version="1.0"?><malicious>payload</malicious>',
                "expected_parsing": "json",
            },
            # Text with JSON structure
            {
                "content_type": "text/plain",
                "payload": '{"admin": true}',
                "expected_parsing": "text",
            },
            # Multipart in JSON context
            {
                "content_type": "application/json",
                "payload": (
                    "--boundary\r\nContent-Disposition: form-data; "
                    'name="admin"\r\n\r\ntrue\r\n--boundary--'
                ),
                "expected_parsing": "json",
            },
        ]

        for attack in confusion_attacks:
            response = pentesting_client.post(
                "/api/keys/validate",
                content=attack["payload"],
                headers={"Content-Type": attack["content_type"]},
            )

            # Should not be confused by content-type mismatches
            assert response.status_code in [400, 401, 403, 422], (
                f"Content-type confusion attack succeeded: {attack['content_type']}"
            )

    async def test_cache_poisoning_simulation(self, pentesting_client):
        """Test cache poisoning attack simulation."""
        # Cache poisoning vectors
        poisoning_attempts = [
            # Header pollution
            {
                "headers": {
                    "Host": "evil.com",
                    "X-Forwarded-Host": "malicious.com",
                    "X-Original-URL": "/admin/backdoor",
                    "X-Rewrite-URL": "/admin/users",
                }
            },
            # Cache key manipulation
            {
                "headers": {
                    "X-Cache-Key": "admin_bypass",
                    "Vary": "Authorization",
                    "Cache-Control": "public, max-age=3600",
                }
            },
            # HTTP smuggling simulation
            {
                "headers": {
                    "Transfer-Encoding": "chunked",
                    "Content-Length": "100",
                    "X-HTTP-Method-Override": "GET",
                }
            },
        ]

        for attempt in poisoning_attempts:
            response = pentesting_client.get(
                "/api/sensitive/data", headers=attempt["headers"]
            )

            # Should not be vulnerable to cache poisoning
            assert response.status_code in [400, 401, 403]

            # Check that no malicious cache directives are honored
            cache_control = response.headers.get("Cache-Control", "")
            assert "public" not in cache_control or "max-age" not in cache_control


class TestSecurityMisconfigurationExploitation:
    """Penetration tests targeting security misconfigurations."""

    async def test_debug_mode_information_disclosure(self, pentesting_client):
        """Test exploitation of debug mode misconfigurations."""
        # Debug mode detection vectors
        debug_indicators = [
            "/api/debug",
            "/api/__debug__",
            "/api/trace",
            "/api/error",
            "/api/exception",
        ]

        debug_headers = [
            "X-Debug",
            "X-Trace",
            "Debug",
            "Trace-Id",
            "X-Request-ID",
            "X-Correlation-ID",
        ]

        debug_params = [
            {"debug": "true"},
            {"trace": "1"},
            {"verbose": "true"},
            {"dev": "1"},
            {"test": "true"},
        ]

        # Test debug endpoints
        for endpoint in debug_indicators:
            response = pentesting_client.get(endpoint)
            assert response.status_code in [401, 403, 404], (
                f"Debug endpoint exposed: {endpoint}"
            )

        # Test debug headers
        for header in debug_headers:
            response = pentesting_client.get(
                "/api/sensitive/data", headers={header: "enabled"}
            )
            # Should not enable debug mode via headers
            if response.status_code == 200:
                content = response.text.lower()
                debug_terms = ["debug", "trace", "exception", "stack", "error"]
                for term in debug_terms:
                    assert term not in content, (
                        f"Debug information leaked via {header} header"
                    )

        # Test debug parameters
        for params in debug_params:
            response = pentesting_client.get("/api/sensitive/data", params=params)
            # Should not enable debug mode via parameters
            if response.status_code == 200:
                assert len(response.content) < 5000, (
                    "Excessive debug information in response"
                )

    async def test_cors_misconfiguration_exploitation(self, pentesting_client):
        """Test CORS misconfiguration exploitation."""
        # CORS exploitation vectors
        malicious_origins = [
            "https://evil.com",
            "http://malicious.domain.com",
            "https://subdomain.evil.com",
            "null",
            "*",
            "https://company.com.evil.com",
        ]

        for origin in malicious_origins:
            response = pentesting_client.get(
                "/api/sensitive/data", headers={"Origin": origin}
            )

            # Check CORS headers in response
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get(
                    "Access-Control-Allow-Origin"
                ),
                "Access-Control-Allow-Credentials": response.headers.get(
                    "Access-Control-Allow-Credentials"
                ),
                "Access-Control-Allow-Methods": response.headers.get(
                    "Access-Control-Allow-Methods"
                ),
            }

            # Should not allow malicious origins
            if cors_headers["Access-Control-Allow-Origin"]:
                assert cors_headers["Access-Control-Allow-Origin"] != origin, (
                    f"CORS misconfiguration allows {origin}"
                )
                assert cors_headers["Access-Control-Allow-Origin"] != "*", (
                    "CORS allows any origin"
                )

            # Should not allow credentials with wildcard
            if cors_headers["Access-Control-Allow-Origin"] == "*":
                assert cors_headers["Access-Control-Allow-Credentials"] != "true", (
                    "CORS allows credentials with wildcard origin"
                )

    async def test_security_header_bypass_attempts(self, pentesting_client):
        """Test bypassing security headers."""
        # Security header bypass vectors
        bypass_attempts = [
            # CSP bypass
            {
                "header": "Content-Security-Policy",
                "bypass_values": [
                    "default-src 'unsafe-inline'",
                    "script-src 'unsafe-eval'",
                    "object-src *",
                    "base-uri 'unsafe-inline'",
                ],
            },
            # HSTS bypass
            {
                "header": "Strict-Transport-Security",
                "bypass_values": ["max-age=0", "max-age=1", ""],
            },
            # X-Frame-Options bypass
            {
                "header": "X-Frame-Options",
                "bypass_values": ["ALLOWALL", "ALLOW-FROM https://evil.com", ""],
            },
        ]

        for attempt in bypass_attempts:
            for bypass_value in attempt["bypass_values"]:
                response = pentesting_client.get(
                    "/api/sensitive/data", headers={attempt["header"]: bypass_value}
                )

                # Should not accept malicious security header values
                response_header = response.headers.get(attempt["header"], "")
                assert bypass_value not in response_header, (
                    f"Security header bypass: {attempt['header']}"
                )

    async def test_file_upload_security_bypass(self, pentesting_client):
        """Test file upload security bypasses."""
        # Malicious file upload attempts
        malicious_files = [
            # Script files
            {"filename": "shell.php", "content": "<?php system($_GET['cmd']); ?>"},
            {
                "filename": "script.jsp",
                "content": (
                    "<% Runtime.getRuntime().exec(request.getParameter('cmd')); %>"
                ),
            },
            {
                "filename": "backdoor.aspx",
                "content": (
                    "<%@ Page Language='C#' %><script runat='server'>"
                    "void Page_Load(object sender, EventArgs e){}</script>"
                ),
            },
            # Double extension
            {"filename": "image.jpg.php", "content": "<?php phpinfo(); ?>"},
            {"filename": "document.pdf.exe", "content": "MZ\x90\x00\x03malicious"},
            # MIME type confusion
            {
                "filename": "image.jpg",
                "content": "<?php phpinfo(); ?>",
                "content_type": "image/jpeg",
            },
            {
                "filename": "document.pdf",
                "content": "<script>alert('xss')</script>",
                "content_type": "application/pdf",
            },
            # Path traversal
            {
                "filename": "../../etc/passwd",
                "content": "root:x:0:0:root:/root:/bin/bash",
            },
            {"filename": "../config.ini", "content": "[admin]\npassword=secret"},
        ]

        for malicious_file in malicious_files:
            # Simulate file upload
            files = {
                "file": (
                    malicious_file["filename"],
                    malicious_file["content"],
                    malicious_file.get("content_type", "text/plain"),
                )
            }

            response = pentesting_client.post("/api/upload", files=files)

            # Should reject malicious file uploads
            assert response.status_code in [400, 401, 403, 405, 413, 422], (
                f"Malicious file upload accepted: {malicious_file['filename']}"
            )
