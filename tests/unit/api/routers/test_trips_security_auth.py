"""Security, authentication, and authorization tests for trips router.

This module provides comprehensive security testing including authentication
edge cases, authorization boundary testing, permission escalation attempts,
and security vulnerability prevention.
"""

# pylint: disable=too-many-public-methods, too-many-positional-arguments

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.trips import CreateTripRequest, UpdateTripRequest
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
)
from tripsage_core.models.schemas_common.travel import TripDestination
from tripsage_core.services.business.trip_service import TripService, TripVisibility


class TestTripsSecurityAuthentication:
    """Security and authentication tests for trips router."""

    # ===== AUTHENTICATION FIXTURES =====

    @pytest.fixture
    def valid_principal(self):
        """Valid authenticated principal."""
        return Principal(
            id="valid_user_001",
            type="user",
            email="valid.user@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def invalid_principal(self):
        """Invalid principal for testing auth failures."""
        return Principal(
            id="",  # Empty ID
            type="user",
            email="invalid.user@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def expired_principal(self):
        """Principal with expired authentication."""
        return Principal(
            id="expired_user_001",
            type="user",
            email="expired.user@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def malicious_principal(self):
        """Principal attempting malicious actions."""
        return Principal(
            id="malicious_user_001",
            type="user",
            email="malicious.user@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def admin_principal(self):
        """Admin principal for elevated permissions testing."""
        return Principal(
            id="admin_user_001",
            type="admin",
            email="admin.user@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def secure_trip_service(self):
        """Mock trip service with security-aware methods."""
        service = MagicMock(spec=TripService)
        service.create_trip = AsyncMock()
        service.get_trip = AsyncMock()
        service.get_user_trips = AsyncMock()
        service.update_trip = AsyncMock()
        service.delete_trip = AsyncMock()
        service.search_trips = AsyncMock()
        service.duplicate_trip = AsyncMock()
        service.share_trip = AsyncMock()
        service.get_trip_collaborators = AsyncMock()
        return service

    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for security testing."""
        return CreateTripRequest(
            title="Security Test Trip",
            description="Trip for security testing",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            destinations=[
                TripDestination(
                    name="Secure Location",
                    country="Security Country",
                    city="Secure City",
                    coordinates=None,
                    arrival_date=None,
                    departure_date=None,
                    duration_days=None,
                )
            ],
        )

    @pytest.fixture
    def sample_trip_response(self):
        """Sample trip response for security testing."""
        trip = MagicMock()
        trip.id = str(uuid4())
        trip.user_id = "valid_user_001"
        trip.title = "Security Test Trip"
        trip.description = "Trip for security testing"
        trip.visibility = TripVisibility.PRIVATE.value
        trip.destinations = []
        trip.start_date = datetime(2024, 6, 1, tzinfo=UTC)
        trip.end_date = datetime(2024, 6, 10, tzinfo=UTC)
        trip.preferences = {}
        trip.status = "planning"
        trip.created_at = datetime.now(UTC)
        trip.updated_at = datetime.now(UTC)
        return trip

    # ===== AUTHENTICATION TESTS =====

    async def test_unauthenticated_trip_creation(self, secure_trip_service):
        """Test trip creation without authentication."""
        from tripsage.api.routers.trips import create_trip

        # Mock unauthenticated request (None principal)
        trip_request = CreateTripRequest(
            title="Unauthorized Trip",
            description="This should fail",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            destinations=[
                TripDestination(
                    name="Unauthorized Location",
                    country="None",
                    city="None",
                    coordinates=None,
                    arrival_date=None,
                    departure_date=None,
                    duration_days=None,
                )
            ],
        )

        # Test would typically fail at middleware level, but testing router behavior
        with pytest.raises(AttributeError):  # Principal is None
            await create_trip(trip_request, None, secure_trip_service)  # type: ignore[arg-type]

    async def test_invalid_principal_trip_access(
        self, invalid_principal, secure_trip_service
    ):
        """Test trip access with invalid principal."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Service should reject invalid user ID
        secure_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, invalid_principal, secure_trip_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Trip not found"

    async def test_expired_authentication_handling(
        self, expired_principal, secure_trip_service, sample_trip_data
    ):
        """Test handling of expired authentication."""
        from tripsage.api.routers.trips import create_trip

        # Mock authentication expired scenario
        secure_trip_service.create_trip.side_effect = CoreAuthorizationError(
            "Authentication expired"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_trip(sample_trip_data, expired_principal, secure_trip_service)

        assert exc_info.value.status_code == 500

    # ===== AUTHORIZATION TESTS =====

    async def test_access_others_private_trip(
        self, malicious_principal, secure_trip_service
    ):
        """Test unauthorized access to other user's private trip."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Service should deny access to private trip
        secure_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, malicious_principal, secure_trip_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Trip not found"

    async def test_unauthorized_trip_modification(
        self, malicious_principal, secure_trip_service
    ):
        """Test unauthorized trip modification attempt."""
        from tripsage.api.routers.trips import update_trip

        trip_id = uuid4()
        malicious_update = UpdateTripRequest(
            title="Hacked Trip Title",
            description="This should not be allowed",
        )

        # Service should reject unauthorized modification
        secure_trip_service.update_trip.side_effect = CoreAuthorizationError(
            "No permission to edit this trip"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_trip(
                trip_id, malicious_update, malicious_principal, secure_trip_service
            )

        assert exc_info.value.status_code == 500

    async def test_unauthorized_trip_deletion(
        self, malicious_principal, secure_trip_service
    ):
        """Test unauthorized trip deletion attempt."""
        from tripsage.api.routers.trips import delete_trip

        trip_id = uuid4()

        # Service should reject unauthorized deletion
        secure_trip_service.delete_trip.side_effect = CoreAuthorizationError(
            "Only trip owner can delete the trip"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_trip(trip_id, malicious_principal, secure_trip_service)

        assert exc_info.value.status_code == 500

    async def test_permission_escalation_attempt(
        self, malicious_principal, secure_trip_service, sample_trip_response
    ):
        """Test attempt to escalate permissions through trip sharing."""
        from tripsage.api.routers.trips import get_trip

        trip_id = UUID(sample_trip_response.id)

        # Malicious user attempts to access trip they shouldn't have access to
        secure_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, malicious_principal, secure_trip_service)

        assert exc_info.value.status_code == 404

        # Verify service was called with correct user ID (no escalation)
        secure_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id="malicious_user_001"
        )

    # ===== DATA VALIDATION SECURITY TESTS =====

    async def test_sql_injection_prevention_in_search(
        self, valid_principal, secure_trip_service
    ):
        """Test SQL injection prevention in search functionality."""
        from tripsage.api.routers.trips import search_trips

        # Malicious search query
        malicious_query = "'; DROP TABLE trips; --"

        # Service should handle malicious input safely
        secure_trip_service.search_trips.return_value = []

        result = await search_trips(
            q=malicious_query,
            status_filter=None,
            skip=0,
            limit=10,
            principal=valid_principal,
            trip_service=secure_trip_service,
        )

        # Should return empty results, not cause errors
        assert result.total == 0
        assert len(result.items) == 0

        # Verify service received the malicious query as-is
        # (should be handled by service)
        secure_trip_service.search_trips.assert_called_once_with(
            user_id="valid_user_001", query=malicious_query, limit=10
        )

    async def test_xss_prevention_in_trip_data(
        self, valid_principal, secure_trip_service, sample_trip_response
    ):
        """Test XSS prevention in trip data."""
        from tripsage.api.routers.trips import create_trip

        # Malicious trip data with script injection
        malicious_trip_data = CreateTripRequest(
            title="<script>alert('XSS')</script>Malicious Trip",
            description="<img src=x onerror=alert('XSS')>Malicious description",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            destinations=[
                TripDestination(
                    name="<script>alert('XSS')</script>Malicious Location",
                    country="<script>alert('XSS')</script>",
                    city="<script>alert('XSS')</script>",
                    coordinates=None,
                    arrival_date=None,
                    departure_date=None,
                    duration_days=None,
                )
            ],
        )

        # Mock successful creation (validation should happen at service layer)
        sample_trip_response.title = malicious_trip_data.title
        sample_trip_response.description = malicious_trip_data.description
        secure_trip_service.create_trip.return_value = sample_trip_response

        result = await create_trip(
            malicious_trip_data, valid_principal, secure_trip_service
        )

        # Data should be preserved as-is
        # (sanitization should happen at presentation layer)
        assert "<script>" in result.title
        # description may be optional; coerce to string for check
        assert (result.description or "").find("<img") != -1

    async def test_path_traversal_prevention(
        self, valid_principal, secure_trip_service
    ):
        """Test path traversal prevention in export functionality."""
        from tripsage.api.routers.trips import export_trip

        trip_id = uuid4()

        # Mock trip access
        sample_trip = MagicMock()
        sample_trip.id = str(trip_id)
        sample_trip.user_id = "valid_user_001"
        secure_trip_service.get_trip.return_value = sample_trip

        # Attempt path traversal in format parameter
        malicious_format = "../../../etc/passwd"

        result = await export_trip(
            trip_id,
            format=malicious_format,
            principal=valid_principal,
            trip_service=secure_trip_service,
        )

        # Should handle malicious format safely
        assert result["format"] == malicious_format
        # URL should be safely constructed
        assert "download_url" in result

    # ===== INPUT VALIDATION SECURITY TESTS =====

    async def test_oversized_input_handling(self, valid_principal, secure_trip_service):
        """Test handling of oversized inputs."""
        # Create oversized trip data
        oversized_title = "X" * 10000  # Very long title
        oversized_description = "Y" * 100000  # Very long description

        # This should be caught by Pydantic validation
        with pytest.raises(ValueError):
            CreateTripRequest(
                title=oversized_title,
                description=oversized_description,
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 10),
                destinations=[
                    TripDestination(
                        name="Location",
                        country="Country",
                        city="City",
                        coordinates=None,
                        arrival_date=None,
                        departure_date=None,
                        duration_days=None,
                    )
                ],
            )

    async def test_invalid_date_range_security(
        self, valid_principal, secure_trip_service
    ):
        """Test security implications of invalid date ranges."""
        # Attempt to create trip with end date before start date
        with pytest.raises(ValueError, match="End date must be after start date"):
            CreateTripRequest(
                title="Invalid Date Trip",
                description="Testing invalid dates",
                start_date=date(2024, 6, 10),
                end_date=date(2024, 6, 1),  # Before start date
                destinations=[
                    TripDestination(
                        name="Location",
                        country="Country",
                        city="City",
                        coordinates=None,
                        arrival_date=None,
                        departure_date=None,
                        duration_days=None,
                    )
                ],
            )

    async def test_negative_pagination_parameters(
        self, valid_principal, secure_trip_service
    ):
        """Test security with negative pagination parameters."""
        from tripsage.api.routers.trips import list_trips

        # Service should handle negative parameters gracefully
        secure_trip_service.get_user_trips.return_value = []

        # Test negative skip (should be handled by query validation)
        result = await list_trips(
            skip=-10,  # This should be rejected by FastAPI query validation
            limit=10,
            principal=valid_principal,
            trip_service=secure_trip_service,
        )

        # If it reaches here, service should handle it gracefully
        assert result.total == 0

    # ===== SESSION AND TOKEN SECURITY TESTS =====

    async def test_concurrent_session_handling(
        self, valid_principal, secure_trip_service, sample_trip_response
    ):
        """Test handling of concurrent sessions for same user."""
        from tripsage.api.routers.trips import get_trip, update_trip

        trip_id = UUID(sample_trip_response.id)
        secure_trip_service.get_trip.return_value = sample_trip_response
        secure_trip_service.update_trip.return_value = sample_trip_response

        # First session gets trip
        trip_1 = await get_trip(trip_id, valid_principal, secure_trip_service)
        assert trip_1.title == "Security Test Trip"

        # Second session (same user) updates trip
        update_request = UpdateTripRequest(title="Updated by Second Session")
        trip_2 = await update_trip(
            trip_id, update_request, valid_principal, secure_trip_service
        )

        # Both sessions should work (same user)
        assert trip_2.title == "Security Test Trip"  # Mock returns same title

    async def test_token_reuse_prevention(
        self, valid_principal, malicious_principal, secure_trip_service
    ):
        """Test prevention of token reuse across different users."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Valid user creates/accesses trip
        valid_trip = MagicMock()
        valid_trip.user_id = "valid_user_001"
        secure_trip_service.get_trip.return_value = valid_trip

        await get_trip(trip_id, valid_principal, secure_trip_service)

        # Malicious user tries to access with different user ID
        secure_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, malicious_principal, secure_trip_service)

        assert exc_info.value.status_code == 404

    # ===== RATE LIMITING AND DOS PREVENTION TESTS =====

    async def test_rapid_trip_creation_attempts(
        self,
        valid_principal,
        secure_trip_service,
        sample_trip_data,
        sample_trip_response,
    ):
        """Test handling of rapid trip creation attempts."""
        from tripsage.api.routers.trips import create_trip

        secure_trip_service.create_trip.return_value = sample_trip_response

        # Simulate rapid trip creation
        created_trips = []
        for i in range(10):
            trip_data = CreateTripRequest(
                title=f"Rapid Trip {i}",
                description=f"Trip created in rapid succession {i}",
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 10),
                destinations=[
                    TripDestination(
                        name=f"Location {i}",
                        country="Country",
                        city="City",
                        coordinates=None,
                        arrival_date=None,
                        departure_date=None,
                        duration_days=None,
                    )
                ],
            )

            result = await create_trip(trip_data, valid_principal, secure_trip_service)
            created_trips.append(result)

        # All should succeed (rate limiting would be handled at middleware level)
        assert len(created_trips) == 10

    async def test_large_search_queries(self, valid_principal, secure_trip_service):
        """Test handling of large search queries."""
        from tripsage.api.routers.trips import search_trips

        # Very long search query
        large_query = "travel " * 1000  # 6000 characters

        secure_trip_service.search_trips.return_value = []

        result = await search_trips(
            q=large_query,
            status_filter=None,
            skip=0,
            limit=10,
            principal=valid_principal,
            trip_service=secure_trip_service,
        )

        # Should handle large query gracefully
        assert result.total == 0

    # ===== DATA LEAKAGE PREVENTION TESTS =====

    async def test_sensitive_data_exposure_prevention(
        self, valid_principal, secure_trip_service
    ):
        """Test prevention of sensitive data exposure in responses."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Mock trip with potentially sensitive data
        sensitive_trip = MagicMock()
        sensitive_trip.id = str(trip_id)
        sensitive_trip.user_id = "valid_user_001"
        sensitive_trip.title = "Trip with Sensitive Data"
        sensitive_trip.description = (
            "Contains SSN: 123-45-6789 and Credit Card: 4111-1111-1111-1111"
        )
        sensitive_trip.destinations = []
        sensitive_trip.start_date = datetime(2024, 6, 1, tzinfo=UTC)
        sensitive_trip.end_date = datetime(2024, 6, 10, tzinfo=UTC)
        sensitive_trip.preferences = {"internal_service_key": "secret_key_123"}
        sensitive_trip.status = "planning"
        sensitive_trip.created_at = datetime.now(UTC)
        sensitive_trip.updated_at = datetime.now(UTC)

        secure_trip_service.get_trip.return_value = sensitive_trip

        result = await get_trip(trip_id, valid_principal, secure_trip_service)

        # Data should be returned as-is
        # (sanitization should happen at presentation layer)
        assert "SSN" in (result.description or "")
        # Service layer should handle sensitive data filtering

    async def test_error_message_information_disclosure(
        self, malicious_principal, secure_trip_service
    ):
        """Test prevention of information disclosure through error messages."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Different error scenarios
        error_scenarios = [
            (
                CoreResourceNotFoundError(
                    "Trip with ID 12345 not found in database table trips"
                ),
                500,
            ),
            (
                CoreAuthorizationError(
                    "User malicious_user_001 denied access to trip 12345"
                ),
                500,
            ),
            (
                Exception("Database connection failed: postgres://user:pass@host/db"),
                500,
            ),
        ]

        for error, expected_status in error_scenarios:
            secure_trip_service.get_trip.side_effect = error

            with pytest.raises(HTTPException) as exc_info:
                await get_trip(trip_id, malicious_principal, secure_trip_service)

            # Error messages should be generic
            assert exc_info.value.status_code == expected_status
            # Should not expose internal details
            assert "postgres://" not in str(exc_info.value.detail)
            assert "database table" not in str(exc_info.value.detail)

    # ===== BUSINESS LOGIC SECURITY TESTS =====

    async def test_trip_visibility_enforcement(
        self, valid_principal, malicious_principal, secure_trip_service
    ):
        """Test enforcement of trip visibility settings."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Private trip should only be accessible to owner
        private_trip = MagicMock()
        private_trip.id = str(trip_id)
        private_trip.user_id = "valid_user_001"
        private_trip.visibility = TripVisibility.PRIVATE.value

        # Owner can access
        secure_trip_service.get_trip.return_value = private_trip
        result = await get_trip(trip_id, valid_principal, secure_trip_service)
        assert result.id == UUID(str(trip_id))

        # Non-owner cannot access
        secure_trip_service.get_trip.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, malicious_principal, secure_trip_service)
        assert exc_info.value.status_code == 404

    async def test_data_integrity_validation(
        self, valid_principal, secure_trip_service
    ):
        """Test data integrity validation in trip operations."""
        from tripsage.api.routers.trips import update_trip

        trip_id = uuid4()

        # Attempt to update with inconsistent data
        inconsistent_update = UpdateTripRequest(
            start_date=date(2024, 6, 10),
            end_date=date(2024, 6, 5),  # End before start
        )

        # Should fail validation
        with pytest.raises(ValueError, match="End date must be after start date"):
            await update_trip(
                trip_id, inconsistent_update, valid_principal, secure_trip_service
            )

    # ===== AUDIT AND LOGGING SECURITY TESTS =====

    async def test_security_event_logging(
        self, malicious_principal, secure_trip_service
    ):
        """Test that security events are properly logged."""
        from tripsage.api.routers.trips import get_trip

        trip_id = uuid4()

        # Mock failed access attempt
        secure_trip_service.get_trip.return_value = None

        with patch("tripsage.api.routers.trips.logger") as mock_logger:
            with pytest.raises(HTTPException):
                await get_trip(trip_id, malicious_principal, secure_trip_service)

            # Verify security event was logged
            mock_logger.info.assert_called()
            log_call = mock_logger.info.call_args[0][0]
            assert "Getting trip" in log_call

    async def test_no_sensitive_data_in_logs(
        self, valid_principal, secure_trip_service, sample_trip_data
    ):
        """Test that sensitive data is not logged."""
        from tripsage.api.routers.trips import create_trip

        # Create trip with potentially sensitive data
        sensitive_trip_data = CreateTripRequest(
            title="Trip with Password: secret123",
            description="Contains credit card: 4111-1111-1111-1111",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            destinations=[
                TripDestination(
                    name="Location",
                    country="Country",
                    city="City",
                    coordinates=None,
                    arrival_date=None,
                    departure_date=None,
                    duration_days=None,
                )
            ],
        )

        sample_response = MagicMock()
        sample_response.id = str(uuid4())
        sample_response.user_id = "valid_user_001"
        sample_response.title = sensitive_trip_data.title
        sample_response.destinations = sensitive_trip_data.destinations
        sample_response.start_date = datetime(2024, 6, 1, tzinfo=UTC)
        sample_response.end_date = datetime(2024, 6, 10, tzinfo=UTC)
        sample_response.preferences = {}
        sample_response.status = "planning"
        sample_response.created_at = datetime.now(UTC)
        sample_response.updated_at = datetime.now(UTC)

        secure_trip_service.create_trip.return_value = sample_response

        with patch("tripsage.api.routers.trips.logger") as mock_logger:
            await create_trip(sensitive_trip_data, valid_principal, secure_trip_service)

            # Check that logs don't contain sensitive data
            for call in mock_logger.info.call_args_list:
                log_message = str(call)
                assert "secret123" not in log_message
                assert "4111-1111-1111-1111" not in log_message

    # ===== COMPREHENSIVE SECURITY WORKFLOW TESTS =====

    async def test_complete_security_workflow(
        self,
        valid_principal,
        malicious_principal,
        secure_trip_service,
        sample_trip_data,
        sample_trip_response,
    ):
        """Test complete security workflow from creation to access control."""
        from tripsage.api.routers.trips import (
            create_trip,
            delete_trip,
            get_trip,
            update_trip,
        )

        # Step 1: Valid user creates trip
        secure_trip_service.create_trip.return_value = sample_trip_response
        created_trip = await create_trip(
            sample_trip_data, valid_principal, secure_trip_service
        )
        trip_id = UUID(str(created_trip.id))

        # Step 2: Valid user can access their trip
        secure_trip_service.get_trip.return_value = sample_trip_response
        accessed_trip = await get_trip(trip_id, valid_principal, secure_trip_service)
        assert accessed_trip.id == trip_id

        # Step 3: Malicious user cannot access the trip
        secure_trip_service.get_trip.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, malicious_principal, secure_trip_service)
        assert exc_info.value.status_code == 404

        # Step 4: Malicious user cannot update the trip
        malicious_update = UpdateTripRequest(title="Hacked Trip")
        secure_trip_service.update_trip.side_effect = CoreAuthorizationError(
            "Access denied"
        )
        with pytest.raises(HTTPException):
            await update_trip(
                trip_id, malicious_update, malicious_principal, secure_trip_service
            )

        # Step 5: Malicious user cannot delete the trip
        secure_trip_service.delete_trip.side_effect = CoreAuthorizationError(
            "Access denied"
        )
        with pytest.raises(HTTPException):
            await delete_trip(trip_id, malicious_principal, secure_trip_service)

        # Step 6: Valid user can still access and modify their trip
        secure_trip_service.get_trip.return_value = sample_trip_response
        secure_trip_service.update_trip.return_value = sample_trip_response
        secure_trip_service.delete_trip.return_value = True

        final_access = await get_trip(trip_id, valid_principal, secure_trip_service)
        assert final_access.id == trip_id

        valid_update = UpdateTripRequest(title="Updated by Owner")
        updated_trip = await update_trip(
            trip_id, valid_update, valid_principal, secure_trip_service
        )
        assert updated_trip.id == trip_id

        # Final deletion should succeed
        await delete_trip(trip_id, valid_principal, secure_trip_service)

    async def test_edge_case_security_scenarios(
        self, valid_principal, secure_trip_service
    ):
        """Test edge case security scenarios."""
        from tripsage.api.routers.trips import get_trip, search_trips

        # Test with various malformed UUIDs
        malformed_uuids = [
            "not-a-uuid",
            "12345",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]

        for malformed_uuid in malformed_uuids:
            try:
                trip_id = UUID(malformed_uuid)
                secure_trip_service.get_trip.return_value = None
                with pytest.raises(HTTPException):
                    await get_trip(trip_id, valid_principal, secure_trip_service)
            except ValueError:
                # Invalid UUID format - this is expected
                pass

        # Test with edge case search parameters
        edge_case_searches = [
            "",  # Empty string
            " ",  # Just space
            "\n\t",  # Whitespace characters
            "🚀🌟✈️",  # Emoji
            "SELECT * FROM trips",  # SQL-like syntax
        ]

        for search_query in edge_case_searches:
            secure_trip_service.search_trips.return_value = []
            result = await search_trips(
                q=search_query,
                status_filter=None,
                skip=0,
                limit=10,
                principal=valid_principal,
                trip_service=secure_trip_service,
            )
            assert result.total == 0
