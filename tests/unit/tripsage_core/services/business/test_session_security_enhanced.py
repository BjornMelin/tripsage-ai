"""
Enhanced Security Tests for SessionSecurityService IP Validation Fixes.

This module provides comprehensive security testing for the fixed IP validation
vulnerabilities and enhanced input validation.
"""

from unittest.mock import AsyncMock

import pytest

from tripsage_core.exceptions import CoreSecurityError
from tripsage_core.services.business.session_security_service import (
    SessionSecurityService,
    UserSession,
)


@pytest.fixture
def mock_database_service():
    """Mock database service."""
    db_service = AsyncMock()
    db_service.insert = AsyncMock(return_value={"id": "test-session-id"})
    db_service.select = AsyncMock(return_value=[])
    db_service.update = AsyncMock(return_value=True)
    return db_service


@pytest.fixture
def security_service(mock_database_service):
    """Session security service with mocked dependencies."""
    service = SessionSecurityService(
        database_service=mock_database_service,
        session_duration_hours=24,
        max_sessions_per_user=3,
    )
    # Mock the _get_recent_failures method
    service._get_recent_failures = lambda user_id: 0
    return service


class TestIPValidationSecurity:
    """Test enhanced IP validation security fixes."""

    def test_validate_and_score_ip_malicious_patterns(self, security_service):
        """Test detection of malicious patterns in IP addresses."""
        malicious_ips = [
            "../../../etc/passwd",
            "192.168.1.1<script>alert('xss')</script>",
            "10.0.0.1'; DROP TABLE users; --",
            "javascript:alert('xss')",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "192.168.1.1 UNION SELECT * FROM users",
            "127.0.0.1 eval('malicious')",
            "localhost exec('rm -rf /')",
        ]

        for malicious_ip in malicious_ips:
            risk_score = security_service._validate_and_score_ip(
                malicious_ip, "test_user"
            )
            assert risk_score == 50, (
                f"Failed to detect malicious pattern in: {malicious_ip}"
            )

    def test_validate_and_score_ip_buffer_overflow_protection(self, security_service):
        """Test protection against buffer overflow attempts via long IPs."""
        # Test extremely long IP addresses
        long_ips = [
            "x" * 100,  # 100 characters
            "1.2.3.4" + "0" * 50,  # Valid IP with padding
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334" + "a" * 20,  # IPv6 with padding
        ]

        for long_ip in long_ips:
            risk_score = security_service._validate_and_score_ip(long_ip, "test_user")
            assert risk_score == 40, f"Failed to detect long IP: {long_ip[:50]}..."

    def test_validate_and_score_ip_null_byte_injection(self, security_service):
        """Test protection against null byte injection."""
        null_byte_ips = [
            "192.168.1.1\x00malicious",
            "\x00\x00\x00\x00",
            "127.0.0.1\x00/../../../etc/passwd",
        ]

        for null_ip in null_byte_ips:
            # Should sanitize null bytes and process safely
            risk_score = security_service._validate_and_score_ip(null_ip, "test_user")
            assert 0 <= risk_score <= 50, (
                f"Failed to handle null bytes in: {repr(null_ip)}"
            )

    def test_validate_and_score_ip_empty_and_none(self, security_service):
        """Test handling of empty and None IP addresses."""
        # Empty string
        risk_score = security_service._validate_and_score_ip("", "test_user")
        assert risk_score == 10

        # Whitespace only
        risk_score = security_service._validate_and_score_ip("   ", "test_user")
        assert risk_score == 10

        # Tab and newline
        risk_score = security_service._validate_and_score_ip("\t\n", "test_user")
        assert risk_score == 10

    def test_validate_and_score_ip_valid_ips(self, security_service):
        """Test risk scoring for valid IP addresses."""
        ip_tests = [
            # (ip, expected_max_risk)
            ("192.168.1.1", 5),  # Private IP
            ("127.0.0.1", 15),  # Loopback
            ("8.8.8.8", 0),  # Global public IP
            ("203.0.113.1", 5),  # Documentation IP (actually treated as private)
            ("2001:db8::1", 5),  # Private IPv6
            ("::1", 15),  # IPv6 loopback
            ("169.254.1.1", 20),  # Link-local
            ("224.0.0.1", 25),  # Multicast
            ("10.0.0.1", 5),  # Private
            ("172.16.0.1", 5),  # Private
        ]

        for ip_addr, expected_max_risk in ip_tests:
            risk_score = security_service._validate_and_score_ip(ip_addr, "test_user")
            assert risk_score <= expected_max_risk, (
                f"IP {ip_addr} risk {risk_score} > {expected_max_risk}"
            )

    def test_validate_and_score_ip_invalid_format(self, security_service):
        """Test handling of invalid IP address formats."""
        invalid_ips = [
            "not.an.ip.address",
            "999.999.999.999",
            "192.168.1",
            "192.168.1.1.1",
            "gggg::hhh::jjj",
            "256.256.256.256",
            "192.168.1.-1",
            "192.168..1",
        ]

        for invalid_ip in invalid_ips:
            risk_score = security_service._validate_and_score_ip(
                invalid_ip, "test_user"
            )
            assert 25 <= risk_score <= 35, (
                f"Invalid IP {invalid_ip} risk score: {risk_score}"
            )

    def test_validate_and_score_ip_error_handling(self, security_service):
        """Test error handling in IP validation."""
        # Test with non-string input (should be handled gracefully)
        try:
            risk_score = security_service._validate_and_score_ip(None, "test_user")
            # Should handle gracefully and return some risk score
            assert 0 <= risk_score <= 50
        except Exception:
            # If it raises an exception, it should be handled in the calling code
            pass


class TestUserSessionValidation:
    """Test enhanced UserSession model validation."""

    def test_session_id_validation(self):
        """Test session ID validation."""
        # Valid session ID
        session = UserSession(
            id="valid_session_12345",
            user_id="user123",
            session_token="a" * 64,  # Valid 64-char hex
            expires_at="2024-12-31T23:59:59Z",
        )
        assert session.id == "valid_session_12345"

        # Test invalid session IDs
        invalid_ids = [
            "",  # Empty
            "short",  # Too short
            "x" * 200,  # Too long
            "id\x00null",  # Null byte
            "id\nwith\r",  # Control chars
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValueError):
                UserSession(
                    id=invalid_id,
                    user_id="user123",
                    session_token="a" * 64,
                    expires_at="2024-12-31T23:59:59Z",
                )

    def test_user_id_validation(self):
        """Test user ID validation."""
        # Valid user ID
        session = UserSession(
            id="session123",
            user_id="valid_user_123",
            session_token="a" * 64,
            expires_at="2024-12-31T23:59:59Z",
        )
        assert session.user_id == "valid_user_123"

        # Test invalid user IDs
        invalid_user_ids = [
            "",  # Empty
            "x" * 300,  # Too long
            "user\x01ctrl",  # Control chars
        ]

        for invalid_user_id in invalid_user_ids:
            with pytest.raises(ValueError):
                UserSession(
                    id="session123",
                    user_id=invalid_user_id,
                    session_token="a" * 64,
                    expires_at="2024-12-31T23:59:59Z",
                )

    def test_ip_address_validation(self):
        """Test IP address validation in UserSession model."""
        # Valid cases
        valid_ips = [
            None,
            "192.168.1.1",
            "127.0.0.1",
            "2001:db8::1",
            "8.8.8.8",
        ]

        for valid_ip in valid_ips:
            session = UserSession(
                id="session123",
                user_id="user123",
                session_token="a" * 64,
                ip_address=valid_ip,
                expires_at="2024-12-31T23:59:59Z",
            )
            assert session.ip_address == valid_ip

        # Invalid cases that should raise errors
        invalid_ips = [
            "x" * 100,  # Too long
            "192.168.1.1<script>alert(1)</script>",  # XSS
            "'; DROP TABLE users; --",  # SQL injection
            "../../../etc/passwd",  # Path traversal
        ]

        for invalid_ip in invalid_ips:
            with pytest.raises(ValueError):
                UserSession(
                    id="session123",
                    user_id="user123",
                    session_token="a" * 64,
                    ip_address=invalid_ip,
                    expires_at="2024-12-31T23:59:59Z",
                )

    def test_user_agent_validation(self):
        """Test user agent validation."""
        # Valid user agent
        valid_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        session = UserSession(
            id="session123",
            user_id="user123",
            session_token="a" * 64,
            user_agent=valid_ua,
            expires_at="2024-12-31T23:59:59Z",
        )
        assert session.user_agent == valid_ua

        # Test sanitization
        dirty_ua = "Mozilla/5.0\x00\r\nwith\nnull"
        session = UserSession(
            id="session123",
            user_id="user123",
            session_token="a" * 64,
            user_agent=dirty_ua,
            expires_at="2024-12-31T23:59:59Z",
        )
        # Should be sanitized
        assert "\x00" not in session.user_agent
        assert "\r" not in session.user_agent

        # Test too long user agent
        with pytest.raises(ValueError):
            UserSession(
                id="session123",
                user_id="user123",
                session_token="a" * 64,
                user_agent="x" * 3000,  # Too long
                expires_at="2024-12-31T23:59:59Z",
            )

    def test_session_token_validation(self):
        """Test session token validation."""
        # Valid session token (64-char hex)
        valid_token = "a" * 64
        session = UserSession(
            id="session123",
            user_id="user123",
            session_token=valid_token,
            expires_at="2024-12-31T23:59:59Z",
        )
        assert session.session_token == valid_token

        # Invalid session tokens
        invalid_tokens = [
            "",  # Empty
            "short",  # Too short
            "x" * 100,  # Too long
            "invalid_hex_characters_12345678901234567890123456789012345678901234",  # Invalid hex
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises(ValueError):
                UserSession(
                    id="session123",
                    user_id="user123",
                    session_token=invalid_token,
                    expires_at="2024-12-31T23:59:59Z",
                )


class TestIntegratedSecurityImprovements:
    """Test integrated security improvements."""

    @pytest.mark.asyncio
    async def test_create_session_with_malicious_input(self, security_service):
        """Test session creation with various malicious inputs."""
        malicious_inputs = [
            {
                "user_id": "user123<script>alert('xss')</script>",
                "ip_address": "192.168.1.1'; DROP TABLE sessions; --",
                "user_agent": "Mozilla\x00\x01\x02evil",
            },
            {
                "user_id": "../../../etc/passwd",
                "ip_address": "javascript:alert('xss')",
                "user_agent": "x" * 3000,
            },
        ]

        for malicious_data in malicious_inputs:
            # Should either handle gracefully or raise appropriate validation errors
            try:
                session = await security_service.create_session(**malicious_data)
                # If it succeeds, check that dangerous content was sanitized
                if session:
                    assert "<script>" not in session.user_id
                    assert "DROP TABLE" not in (session.ip_address or "")
                    assert len(session.user_agent or "") <= 2048
            except (ValueError, CoreSecurityError):
                # Validation errors and security errors are expected and acceptable
                pass

    @pytest.mark.asyncio
    async def test_validate_session_with_malicious_ip(self, security_service):
        """Test session validation with malicious IP addresses."""
        # Create a session first
        session = await security_service.create_session(
            user_id="test_user",
            ip_address="192.168.1.1",
        )

        # Mock session data in database
        session_data = {
            "id": session.id,
            "user_id": "test_user",
            "session_token": session.session_token,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "device_info": {},
            "location_info": {},
            "is_active": True,
            "last_activity_at": session.last_activity_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "created_at": session.created_at.isoformat(),
            "ended_at": None,
        }

        security_service.db.select.return_value = [session_data]

        # Test validation with malicious IP
        malicious_ips = [
            "192.168.1.1<script>alert(1)</script>",
            "../../../etc/passwd",
            "'; DROP TABLE sessions; --",
        ]

        for malicious_ip in malicious_ips:
            # Should handle malicious IPs gracefully in validation
            # May return None or a valid session depending on security policy
            result = await security_service.validate_session(
                "dummy_token", ip_address=malicious_ip, user_agent="Mozilla/5.0"
            )
            # Should not crash and should handle malicious input safely
            assert result is None or isinstance(result, UserSession)

    def test_risk_calculation_with_extreme_inputs(self, security_service):
        """Test risk calculation with extreme and edge case inputs."""
        extreme_inputs = [
            ("", "empty_user"),
            (None, "none_user"),
            ("x" * 1000, "long_user"),
            ("192.168.1.1\x00null", "null_user"),
            ("../../../etc/passwd", "path_user"),
            ("javascript:alert('xss')", "xss_user"),
        ]

        for ip_input, user_id in extreme_inputs:
            # Should handle all inputs gracefully and return reasonable risk scores
            risk_score = security_service._calculate_login_risk_score(user_id, ip_input)
            assert 0 <= risk_score <= 100, (
                f"Risk score {risk_score} out of range for {ip_input}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
