"""
Comprehensive XSS and CSRF protection tests for API endpoints.

This module provides security testing for Cross-Site Scripting (XSS) and 
Cross-Site Request Forgery (CSRF) protection mechanisms in the API key 
validation infrastructure. Tests cover both input validation and HTTP 
header security configurations.

Based on OWASP WSTG 2024 guidelines and FastAPI security best practices.
"""

import json
import re
import uuid
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.schemas.api_keys import ApiKeyCreate, ApiKeyValidateRequest
from tripsage_core.services.business.api_key_service import (
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class TestXSSProtection:
    """Test suite for Cross-Site Scripting (XSS) protection."""

    @pytest.fixture
    def xss_payloads(self) -> List[str]:
        """Common XSS attack payloads from OWASP WSTG."""
        return [
            # Basic XSS payloads
            "<script>alert('XSS')</script>",
            "<script>alert(document.cookie)</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            
            # Encoded XSS payloads
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            
            # Attribute-based XSS
            "javascript:alert('XSS')",
            "\" onfocus=\"alert('XSS')",
            "' onfocus='alert('XSS')",
            
            # Event handler XSS
            "onmouseover=alert('XSS')",
            "onclick=alert('XSS')",
            "onerror=alert('XSS')",
            
            # Advanced XSS bypasses
            "<scr<script>ipt>alert('XSS')</script>",
            "<ScRiPt>alert('XSS')</ScRiPt>",
            "<script >alert('XSS')</script >",
            
            # HTML injection
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            "<embed src='javascript:alert(\"XSS\")'></embed>",
            
            # CSS-based XSS
            "<style>@import'javascript:alert(\"XSS\")';</style>",
            "<link rel='stylesheet' href='javascript:alert(\"XSS\")'>",
            
            # Data URI XSS
            "data:text/html,<script>alert('XSS')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
            
            # DOM-based XSS patterns
            "<script>document.write('<img src=x onerror=alert(\"XSS\")/>')</script>",
            "<script>eval('alert(\"XSS\")')</script>",
            "<script>setTimeout('alert(\"XSS\")', 1000)</script>",
        ]

    @pytest.fixture
    def html_injection_payloads(self) -> List[str]:
        """HTML injection payloads for content injection testing."""
        return [
            "<h1>Injected Content</h1>",
            "<div>Malicious Content</div>",
            "<p style='color:red'>Styled Injection</p>",
            "<marquee>Moving Text Injection</marquee>",
            "<table><tr><td>Table Injection</td></tr></table>",
            "<!-- Injected Comment -->",
            "<meta http-equiv='refresh' content='0;url=http://evil.com'>",
            "<base href='http://evil.com/'>",
        ]

    @pytest.fixture
    def test_client(self) -> TestClient:
        """FastAPI test client with mocked dependencies."""
        return TestClient(app)

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal for testing."""
        return Mock(
            id="test-user-123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={}
        )

    def test_api_key_name_xss_protection(self, test_client, xss_payloads, mock_principal):
        """Test XSS protection in API key name field."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                with patch("tripsage_core.services.business.api_key_service.get_api_key_service") as mock_service:
                    mock_key_service = AsyncMock()
                    mock_service.return_value = mock_key_service
                    
                    # Mock validation to succeed
                    mock_key_service.validate_key.return_value = ValidationResult(
                        is_valid=True,
                        status=ValidationStatus.VALID,
                        message="Valid key"
                    )
                    
                    for payload in xss_payloads:
                        api_key_data = {
                            "name": payload,
                            "service": "openai",
                            "key": "sk-test_key_123",
                            "description": "Test key"
                        }
                        
                        response = test_client.post("/api/keys", json=api_key_data)
                        
                        # Should not return XSS payload in response
                        response_text = response.text
                        assert "<script>" not in response_text
                        assert "javascript:" not in response_text
                        assert "onerror=" not in response_text
                        assert "onclick=" not in response_text
                        
                        # Should not execute JavaScript in name validation
                        if "alert" in payload:
                            assert "alert" not in response_text or "alert" in str(response.status_code)

    def test_api_key_description_xss_protection(self, test_client, xss_payloads, mock_principal):
        """Test XSS protection in API key description field."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                with patch("tripsage_core.services.business.api_key_service.get_api_key_service") as mock_service:
                    mock_key_service = AsyncMock()
                    mock_service.return_value = mock_key_service
                    
                    mock_key_service.validate_key.return_value = ValidationResult(
                        is_valid=True,
                        status=ValidationStatus.VALID,
                        message="Valid key"
                    )
                    
                    for payload in xss_payloads:
                        api_key_data = {
                            "name": "Test Key",
                            "service": "openai", 
                            "key": "sk-test_key_123",
                            "description": payload
                        }
                        
                        response = test_client.post("/api/keys", json=api_key_data)
                        
                        # Should sanitize description field
                        response_text = response.text
                        assert "<script>" not in response_text
                        assert "javascript:" not in response_text
                        assert payload not in response_text or response.status_code >= 400

    def test_html_injection_in_error_messages(self, test_client, html_injection_payloads, mock_principal):
        """Test HTML injection protection in error messages."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                with patch("tripsage_core.services.business.api_key_service.get_api_key_service") as mock_service:
                    mock_key_service = AsyncMock()
                    mock_service.return_value = mock_key_service
                    
                    # Mock validation to fail with error message containing payload
                    for payload in html_injection_payloads:
                        mock_key_service.validate_key.return_value = ValidationResult(
                            is_valid=False,
                            status=ValidationStatus.INVALID,
                            message=f"Invalid key: {payload}"
                        )
                        
                        api_key_data = {
                            "name": "Test Key",
                            "service": "openai",
                            "key": "sk-invalid_key",
                            "description": "Test"
                        }
                        
                        response = test_client.post("/api/keys", json=api_key_data)
                        
                        # Error message should not contain raw HTML
                        response_text = response.text
                        assert "<h1>" not in response_text
                        assert "<div>" not in response_text
                        assert "<script>" not in response_text
                        assert "<meta" not in response_text

    def test_xss_in_validation_request(self, test_client, xss_payloads, mock_principal):
        """Test XSS protection in key validation requests."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                with patch("tripsage_core.services.business.api_key_service.get_api_key_service") as mock_service:
                    mock_key_service = AsyncMock()
                    mock_service.return_value = mock_key_service
                    
                    for payload in xss_payloads:
                        validation_data = {
                            "key": payload,
                            "service": "openai"
                        }
                        
                        response = test_client.post("/api/keys/validate", json=validation_data)
                        
                        # Response should not contain unescaped XSS payload
                        response_text = response.text
                        assert payload not in response_text or response.status_code >= 400
                        assert "<script>" not in response_text
                        assert "javascript:" not in response_text

    def test_content_type_header_validation(self, test_client, mock_principal):
        """Test Content-Type header validation prevents XSS."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Test with text/html content type (should be rejected)
            response = test_client.post(
                "/api/keys",
                data="<script>alert('XSS')</script>",
                headers={"Content-Type": "text/html"}
            )
            
            # Should reject HTML content type
            assert response.status_code in [400, 415, 422]
            assert "<script>" not in response.text

    def test_user_agent_header_xss_protection(self, test_client, xss_payloads):
        """Test User-Agent header XSS protection."""
        for payload in xss_payloads[:5]:  # Test subset for performance
            headers = {"User-Agent": payload}
            
            response = test_client.get("/api/keys", headers=headers)
            
            # User-Agent should not be reflected in response
            response_text = response.text
            assert payload not in response_text
            assert "<script>" not in response_text

    def test_referer_header_xss_protection(self, test_client, xss_payloads):
        """Test Referer header XSS protection."""
        for payload in xss_payloads[:5]:  # Test subset for performance
            headers = {"Referer": f"http://example.com/{payload}"}
            
            response = test_client.get("/api/keys", headers=headers)
            
            # Referer should not be reflected in response
            response_text = response.text
            assert payload not in response_text
            assert "<script>" not in response_text


class TestCSRFProtection:
    """Test suite for Cross-Site Request Forgery (CSRF) protection."""

    @pytest.fixture
    def test_client(self) -> TestClient:
        """FastAPI test client for CSRF testing."""
        return TestClient(app)

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Mock(
            id="test-user-123",
            type="user", 
            email="test@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={}
        )

    def test_state_changing_operations_require_authentication(self, test_client):
        """Test that state-changing operations require authentication."""
        state_changing_endpoints = [
            ("POST", "/api/keys", {"name": "Test", "service": "openai", "key": "sk-test"}),
            ("DELETE", "/api/keys/test-id", None),
            ("POST", "/api/keys/test-id/rotate", {"new_key": "sk-new-test"}),
            ("POST", "/api/keys/validate", {"key": "sk-test", "service": "openai"}),
        ]
        
        for method, endpoint, data in state_changing_endpoints:
            if method == "POST":
                response = test_client.post(endpoint, json=data)
            elif method == "DELETE":
                response = test_client.delete(endpoint)
            
            # Should require authentication
            assert response.status_code == 401
            assert "Authentication" in response.text or "Unauthorized" in response.text

    def test_cors_preflight_request_handling(self, test_client):
        """Test CORS preflight request handling for CSRF protection."""
        # Test preflight request
        response = test_client.options(
            "/api/keys",
            headers={
                "Origin": "http://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should handle CORS appropriately
        assert response.status_code in [200, 404, 405]
        
        # Check for proper CORS headers if allowed
        if "Access-Control-Allow-Origin" in response.headers:
            origin = response.headers.get("Access-Control-Allow-Origin")
            # Should not allow arbitrary origins for state-changing operations
            assert origin != "*" or response.status_code >= 400

    def test_content_type_csrf_protection(self, test_client, mock_principal):
        """Test Content-Type based CSRF protection."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                # Test with simple form content type (potential CSRF vector)
                response = test_client.post(
                    "/api/keys",
                    data="name=Test&service=openai&key=sk-test",
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                # Should reject form-encoded data for JSON API
                assert response.status_code in [400, 415, 422]

    def test_csrf_via_json_with_text_plain(self, test_client, mock_principal):
        """Test CSRF protection against JSON with text/plain content type."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Attempt CSRF with text/plain content type
            malicious_json = '{"name":"hacked","service":"openai","key":"sk-hacked"}'
            
            response = test_client.post(
                "/api/keys",
                data=malicious_json,
                headers={"Content-Type": "text/plain"}
            )
            
            # Should reject text/plain for JSON endpoints
            assert response.status_code in [400, 415, 422]

    def test_same_origin_policy_enforcement(self, test_client, mock_principal):
        """Test enforcement of same-origin policy for state changes."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                # Test with malicious origin header
                response = test_client.post(
                    "/api/keys",
                    json={"name": "Test", "service": "openai", "key": "sk-test"},
                    headers={"Origin": "http://malicious-site.com"}
                )
                
                # Should either reject or handle appropriately
                if response.status_code == 200:
                    # If allowed, check for proper CORS configuration
                    assert "Access-Control-Allow-Origin" not in response.headers or \
                           response.headers.get("Access-Control-Allow-Origin") != "http://malicious-site.com"

    def test_csrf_token_validation_if_implemented(self, test_client):
        """Test CSRF token validation if CSRF protection is implemented."""
        # Attempt request without CSRF token
        response = test_client.post(
            "/api/keys",
            json={"name": "Test", "service": "openai", "key": "sk-test"},
            headers={"X-Requested-With": "XMLHttpRequest"}  # AJAX header
        )
        
        # Should require authentication at minimum
        assert response.status_code in [401, 403]

    def test_state_changing_get_requests_blocked(self, test_client, mock_principal):
        """Test that state-changing operations cannot be performed via GET."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Try to create API key via GET (should fail)
            response = test_client.get(
                "/api/keys?name=Test&service=openai&key=sk-test"
            )
            
            # GET should not create resources
            assert response.status_code in [404, 405]  # Method not allowed or not found

    def test_referrer_policy_header(self, test_client):
        """Test Referrer-Policy header for CSRF protection."""
        response = test_client.get("/api/keys")
        
        # Should set appropriate referrer policy
        if "Referrer-Policy" in response.headers:
            referrer_policy = response.headers["Referrer-Policy"]
            # Should use restrictive referrer policy
            assert referrer_policy in [
                "strict-origin-when-cross-origin",
                "strict-origin",
                "same-origin",
                "no-referrer"
            ]

    def test_authorization_header_csrf_mitigation(self, test_client):
        """Test that Authorization header provides CSRF mitigation."""
        # Requests with Authorization header are less vulnerable to CSRF
        response = test_client.post(
            "/api/keys",
            json={"name": "Test", "service": "openai", "key": "sk-test"},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Should be handled by authentication middleware
        assert response.status_code in [401, 403]  # Invalid token


class TestHTTPSecurityHeaders:
    """Test suite for HTTP security header configurations."""

    @pytest.fixture
    def test_client(self) -> TestClient:
        """FastAPI test client for header testing."""
        return TestClient(app)

    def test_content_security_policy_header(self, test_client):
        """Test Content-Security-Policy header configuration."""
        response = test_client.get("/api/keys")
        
        if "Content-Security-Policy" in response.headers:
            csp = response.headers["Content-Security-Policy"]
            
            # Should have restrictive CSP
            assert "default-src 'self'" in csp or "default-src 'none'" in csp
            # Should not allow unsafe-inline or unsafe-eval
            assert "'unsafe-inline'" not in csp
            assert "'unsafe-eval'" not in csp

    def test_x_frame_options_header(self, test_client):
        """Test X-Frame-Options header for clickjacking protection."""
        response = test_client.get("/api/keys")
        
        if "X-Frame-Options" in response.headers:
            frame_options = response.headers["X-Frame-Options"]
            # Should prevent framing
            assert frame_options in ["DENY", "SAMEORIGIN"]

    def test_x_content_type_options_header(self, test_client):
        """Test X-Content-Type-Options header for MIME sniffing protection."""
        response = test_client.get("/api/keys")
        
        if "X-Content-Type-Options" in response.headers:
            content_type_options = response.headers["X-Content-Type-Options"]
            # Should prevent MIME sniffing
            assert content_type_options == "nosniff"

    def test_x_xss_protection_header(self, test_client):
        """Test X-XSS-Protection header configuration."""
        response = test_client.get("/api/keys")
        
        if "X-XSS-Protection" in response.headers:
            xss_protection = response.headers["X-XSS-Protection"]
            # Should enable XSS protection
            assert "1" in xss_protection
            # Should block rather than filter
            assert "mode=block" in xss_protection

    def test_strict_transport_security_header(self, test_client):
        """Test Strict-Transport-Security header for HTTPS enforcement."""
        response = test_client.get("/api/keys")
        
        if "Strict-Transport-Security" in response.headers:
            hsts = response.headers["Strict-Transport-Security"]
            # Should have reasonable max-age
            assert "max-age=" in hsts
            # Should include subdomains
            assert "includeSubDomains" in hsts

    def test_referrer_policy_header(self, test_client):
        """Test Referrer-Policy header configuration."""
        response = test_client.get("/api/keys")
        
        if "Referrer-Policy" in response.headers:
            referrer_policy = response.headers["Referrer-Policy"]
            # Should use privacy-preserving policy
            assert referrer_policy in [
                "strict-origin-when-cross-origin",
                "strict-origin",
                "same-origin",
                "no-referrer"
            ]

    def test_cache_control_for_sensitive_endpoints(self, test_client, mock_principal):
        """Test Cache-Control headers for sensitive endpoints."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            with patch("tripsage.api.core.dependencies.get_principal_id", return_value="test-user-123"):
                response = test_client.get("/api/keys")
                
                # Sensitive endpoints should not be cached
                if "Cache-Control" in response.headers:
                    cache_control = response.headers["Cache-Control"]
                    assert "no-cache" in cache_control or "no-store" in cache_control

    def test_server_header_information_disclosure(self, test_client):
        """Test that Server header doesn't disclose sensitive information."""
        response = test_client.get("/api/keys")
        
        if "Server" in response.headers:
            server = response.headers["Server"]
            # Should not reveal detailed version information
            sensitive_info = ["uvicorn", "fastapi", "python", "version"]
            disclosed_info = [info for info in sensitive_info if info.lower() in server.lower()]
            # Minimal disclosure is acceptable, but detailed versions should be hidden
            assert len(disclosed_info) <= 1

    def test_content_type_header_consistency(self, test_client):
        """Test Content-Type header consistency for API responses."""
        response = test_client.get("/api/keys")
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            # API should return JSON
            assert "application/json" in content_type

    def test_vary_header_for_security(self, test_client):
        """Test Vary header for caching security."""
        response = test_client.get("/api/keys")
        
        # Should vary on security-sensitive headers
        if "Vary" in response.headers:
            vary = response.headers["Vary"]
            # Common security-sensitive headers
            security_headers = ["Authorization", "Cookie", "Origin"]
            varies_on_security = any(header in vary for header in security_headers)
            # If Vary is set, should consider security headers
            assert varies_on_security or "Accept" in vary


class TestInputValidationSecurity:
    """Test suite for input validation security measures."""

    @pytest.fixture
    def test_client(self) -> TestClient:
        """FastAPI test client for input validation testing."""
        return TestClient(app)

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Mock(
            id="test-user-123",
            type="user",
            email="test@example.com", 
            auth_method="jwt",
            scopes=[],
            metadata={}
        )

    def test_json_injection_protection(self, test_client, mock_principal):
        """Test protection against JSON injection attacks."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Test malformed JSON that could bypass validation
            malformed_payloads = [
                '{"name": "Test", "extra": {"constructor": {"prototype": {"polluted": true}}}}',
                '{"__proto__": {"polluted": true}, "name": "Test"}',
                '{"name": "Test\\u0000Null"}',
                '{"name": "Test\\"", "service": "openai"}',
            ]
            
            for payload in malformed_payloads:
                response = test_client.post(
                    "/api/keys",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Should handle malformed JSON safely
                assert response.status_code in [400, 422]

    def test_parameter_pollution_protection(self, test_client, mock_principal):
        """Test protection against HTTP parameter pollution."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Test duplicate parameters
            response = test_client.post(
                "/api/keys?name=Good&name=Evil",
                json={"name": "Test", "service": "openai", "key": "sk-test"}
            )
            
            # Should handle parameter pollution safely
            if response.status_code == 200:
                # Should use the JSON body, not query parameters
                assert "Evil" not in response.text

    def test_large_payload_protection(self, test_client, mock_principal):
        """Test protection against excessively large payloads."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Create large payload
            large_description = "A" * 1000000  # 1MB description
            
            response = test_client.post(
                "/api/keys",
                json={
                    "name": "Test",
                    "service": "openai",
                    "key": "sk-test",
                    "description": large_description
                }
            )
            
            # Should reject excessively large payloads
            assert response.status_code in [400, 413, 422]

    def test_unicode_normalization_attack_protection(self, test_client, mock_principal):
        """Test protection against Unicode normalization attacks."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Unicode normalization attack payloads
            unicode_payloads = [
                "Test\u0041\u0300",  # A with combining grave accent
                "Test\uFEFF",      # Zero-width no-break space
                "Test\u200B",      # Zero-width space
                "Test\u2028",      # Line separator
                "Test\u2029",      # Paragraph separator
            ]
            
            for payload in unicode_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": payload, "service": "openai", "key": "sk-test"}
                )
                
                # Should handle Unicode safely
                if response.status_code == 200:
                    # Should normalize or reject problematic Unicode
                    assert payload not in response.text or len(response.text) < len(payload)

    def test_control_character_filtering(self, test_client, mock_principal):
        """Test filtering of control characters in input."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Control character payloads
            control_payloads = [
                "Test\x00Null",
                "Test\x01SOH",
                "Test\x08Backspace",
                "Test\x0CForm Feed",
                "Test\x7FDelete",
            ]
            
            for payload in control_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": payload, "service": "openai", "key": "sk-test"}
                )
                
                # Should filter or reject control characters
                if response.status_code == 200:
                    # Should not contain control characters
                    assert "\x00" not in response.text
                    assert "\x01" not in response.text

    def test_path_traversal_in_service_field(self, test_client, mock_principal):
        """Test protection against path traversal in service field."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Path traversal payloads
            traversal_payloads = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "....//....//....//etc/passwd",
            ]
            
            for payload in traversal_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": "Test", "service": payload, "key": "sk-test"}
                )
                
                # Should reject path traversal attempts
                assert response.status_code in [400, 422]

    def test_sql_injection_in_string_fields(self, test_client, mock_principal):
        """Test protection against SQL injection in string fields."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # SQL injection payloads
            sql_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; INSERT INTO users VALUES ('hacker', 'password'); --",
                "' UNION SELECT password FROM users --",
            ]
            
            for payload in sql_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": payload, "service": "openai", "key": "sk-test"}
                )
                
                # Should safely handle SQL injection attempts
                if response.status_code == 200:
                    # Should not execute SQL
                    assert "DROP TABLE" not in response.text
                    assert "INSERT INTO" not in response.text

    def test_command_injection_protection(self, test_client, mock_principal):
        """Test protection against command injection."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # Command injection payloads
            command_payloads = [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /",
                "`whoami`",
                "$(cat /etc/passwd)",
            ]
            
            for payload in command_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": f"Test{payload}", "service": "openai", "key": "sk-test"}
                )
                
                # Should safely handle command injection attempts
                if response.status_code == 200:
                    # Should not execute commands
                    assert "root:" not in response.text
                    assert "/bin/bash" not in response.text

    def test_ldap_injection_protection(self, test_client, mock_principal):
        """Test protection against LDAP injection."""
        with patch("tripsage.api.core.dependencies.require_principal", return_value=mock_principal):
            # LDAP injection payloads
            ldap_payloads = [
                "*)(uid=*",
                "*))%00",
                "*))(|(password=*",
                "*)(|(objectClass=*",
            ]
            
            for payload in ldap_payloads:
                response = test_client.post(
                    "/api/keys",
                    json={"name": f"Test{payload}", "service": "openai", "key": "sk-test"}
                )
                
                # Should safely handle LDAP injection attempts
                assert response.status_code in [200, 400, 422]
                if response.status_code == 200:
                    assert payload not in response.text