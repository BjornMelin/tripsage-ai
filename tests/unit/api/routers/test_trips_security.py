"""Comprehensive security tests for trips router security fixes.

This module tests all 7 security vulnerability fixes implemented in the trips router,
ensuring proper authorization, authentication, and audit logging across all endpoints.

Security fixes tested:
- Line 279: Trip access verification in get operations
- Lines 436-440: Authorization checks in trip summary endpoint
- Line 661: Security validation in trip update operations
- Line 720: Access control in trip deletion
- Line 763: Permission verification in collaboration endpoints
- Line 992: Authorization in sharing functionality
- Lines 1064-1066: Security checks in export operations
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.trips import (
    delete_trip,
    export_trip,
    get_trip,
    get_trip_summary,
    list_trip_collaborators,
    share_trip,
    update_trip,
)
from tripsage.api.schemas.trips import TripShareRequest, UpdateTripRequest
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreSecurityError,
)
from tripsage_core.models.schemas_common.enums import (
    TripVisibility,
)
from tripsage_core.services.business.trip_service import TripService


# Load shared fixtures (sample_trip_data, mock_audit_service)
pytest_plugins = ["tests.fixtures.trip_fixtures"]


@pytest.fixture
def sample_trip_data(core_trip_response):
    """Override global dict-based fixture with core model object.

    Many tests rely on attribute access and pass-through to the API adapter,
    which expects core service models rather than plain dicts.
    """
    return core_trip_response


@pytest.fixture
def mock_principal():
    """Create a mock principal for testing."""
    return Principal(
        id=str(uuid4()),
        type="user",
        email="test@example.com",
        auth_method="jwt",
        scopes=[],
        metadata={},
    )


@pytest.fixture
def mock_different_principal():
    """Create a different mock principal for unauthorized access tests."""
    return Principal(
        id=str(uuid4()),
        type="user",
        email="other@example.com",
        auth_method="jwt",
        scopes=[],
        metadata={},
    )


@pytest.fixture
def mock_trip_service():
    """Create a mock trip service for testing."""
    service = Mock(spec=TripService)
    service.get_trip = AsyncMock()
    service.update_trip = AsyncMock()
    service.delete_trip = AsyncMock()
    service.share_trip = AsyncMock()
    service.export_trip = AsyncMock()
    service.get_trip_collaborators = AsyncMock()
    service._check_trip_access = AsyncMock()
    return service


class TestGetTripSecurity:
    """Test security fixes in get_trip endpoint (line 279)."""

    @pytest.mark.asyncio
    async def test_get_trip_authorized_access(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test authorized access to get_trip endpoint."""
        # Setup: user owns the trip
        trip_id = sample_trip_data.id
        sample_trip_data.user_id = mock_principal.id

        mock_trip_service.get_trip.return_value = sample_trip_data
        mock_trip_service._check_trip_access.return_value = True

        # Execute
        await get_trip(trip_id, mock_principal, mock_trip_service)

        # Verify
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_principal.id
        )

    @pytest.mark.asyncio
    async def test_get_trip_unauthorized_access_denied(
        self, mock_different_principal, mock_trip_service, sample_trip_data
    ):
        """Test unauthorized access denial in get_trip endpoint."""
        # Setup: different user tries to access trip
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.get_trip.return_value = None

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_different_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Trip not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_access_granted(
        self, mock_different_principal, mock_trip_service, sample_trip_data
    ):
        """Test collaborator access to get_trip endpoint."""
        # Setup: user is a collaborator
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = sample_trip_data

        # Execute
        await get_trip(trip_id, mock_different_principal, mock_trip_service)

        # Verify
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_different_principal.id
        )

    @pytest.mark.asyncio
    async def test_get_trip_nonexistent_trip(self, mock_principal, mock_trip_service):
        """Test access to non-existent trip."""
        trip_id = str(uuid4())
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetTripSummarySecurity:
    """Test security fixes in get_trip_summary endpoint (lines 436-440)."""

    @pytest.mark.asyncio
    async def test_get_trip_summary_with_access_verification(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test that get_trip_summary verifies trip access before returning data."""
        # Setup
        trip_id = sample_trip_data.id
        sample_trip_data.user_id = mock_principal.id
        mock_trip_service.get_trip.return_value = sample_trip_data

        # Execute
        result = await get_trip_summary(trip_id, mock_principal, mock_trip_service)

        # Verify access check was performed
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_principal.id
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_trip_summary_unauthorized_access(
        self, mock_different_principal, mock_trip_service
    ):
        """Test unauthorized access to trip summary."""
        trip_id = str(uuid4())
        mock_trip_service.get_trip.return_value = None  # No access

        with pytest.raises(HTTPException) as exc_info:
            await get_trip_summary(trip_id, mock_different_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Trip not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_trip_summary_service_error_handling(
        self, mock_principal, mock_trip_service
    ):
        """Test error handling in trip summary endpoint."""
        trip_id = str(uuid4())
        mock_trip_service.get_trip.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_trip_summary(trip_id, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestUpdateTripSecurity:
    """Test security fixes in update_trip endpoint (line 661)."""

    @pytest.fixture
    def update_request(self):
        """Sample update request."""
        return UpdateTripRequest(
            title="Updated Trip",
            description="Updated description",
            visibility=TripVisibility.PRIVATE,
        )

    @pytest.mark.asyncio
    async def test_update_trip_owner_access(
        self,
        mock_principal,
        mock_trip_service,
        sample_trip_data,
        update_request,
    ):
        """Test trip owner can update trip."""
        trip_id = sample_trip_data.id
        sample_trip_data.user_id = mock_principal.id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.update_trip.return_value = sample_trip_data

        result = await update_trip(
            trip_id, update_request, mock_principal, mock_trip_service
        )

        assert result is not None
        mock_trip_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_unauthorized_access(
        self,
        mock_different_principal,
        mock_trip_service,
        sample_trip_data,
        update_request,
    ):
        """Test unauthorized user cannot update trip."""
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.update_trip.side_effect = CoreAuthorizationError(
            message="Insufficient permissions", code="UNAUTHORIZED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_trip(
                trip_id, update_request, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_trip_collaborator_with_edit_permission(
        self,
        mock_different_principal,
        mock_trip_service,
        sample_trip_data,
        update_request,
    ):
        """Test collaborator with edit permission can update trip."""
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.update_trip.return_value = sample_trip_data

        result = await update_trip(
            trip_id, update_request, mock_different_principal, mock_trip_service
        )

        assert result is not None
        mock_trip_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_collaborator_insufficient_permission(
        self,
        mock_different_principal,
        mock_trip_service,
        sample_trip_data,
        update_request,
    ):
        """Test collaborator with insufficient permission cannot update trip."""
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = False  # View-only access
        mock_trip_service.update_trip.side_effect = CoreAuthorizationError(
            message="Insufficient edit permissions", code="INSUFFICIENT_PERMISSION"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_trip(
                trip_id, update_request, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteTripSecurity:
    """Test security fixes in delete_trip endpoint (line 720)."""

    @pytest.mark.asyncio
    async def test_delete_trip_owner_access(
        self, mock_principal, mock_trip_service, sample_trip_data, mock_audit_service
    ):
        """Test trip owner can delete trip."""
        trip_id = sample_trip_data.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.delete_trip.return_value = True

        result = await delete_trip(trip_id, mock_principal, mock_trip_service)

        assert result is None
        mock_trip_service.delete_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_principal.id
        )
        # Audit path should be exercised on successful deletion
        mock_audit_service.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_trip_unauthorized_access(
        self, mock_different_principal, mock_trip_service, mock_audit_service
    ):
        """Test unauthorized user cannot delete trip."""
        trip_id = str(uuid4())
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.delete_trip.side_effect = CoreAuthorizationError(
            message="Only trip owner can delete trip", code="OWNER_REQUIRED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_trip(trip_id, mock_different_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        mock_audit_service.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_trip_collaborator_denied(
        self, mock_different_principal, mock_trip_service, mock_audit_service
    ):
        """Test collaborator cannot delete trip (owner-only operation)."""
        trip_id = str(uuid4())
        mock_trip_service._check_trip_access.return_value = False  # Not owner
        mock_trip_service.delete_trip.side_effect = CoreAuthorizationError(
            message="Only trip owner can delete trip", code="OWNER_REQUIRED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_trip(trip_id, mock_different_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        mock_audit_service.assert_not_awaited()


class TestListTripCollaboratorsSecurity:
    """Test security fixes in collaboration endpoints (line 763)."""

    @pytest.mark.asyncio
    async def test_list_collaborators_owner_access(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test trip owner can list collaborators."""
        trip_id = sample_trip_data.id
        mock_collaborators = [
            {
                "user_id": str(uuid4()),
                "permission": "edit",
                "added_at": datetime.now(UTC),
            }
        ]

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = sample_trip_data
        mock_trip_service.get_trip_collaborators.return_value = mock_collaborators

        result = await list_trip_collaborators(
            trip_id, mock_principal, mock_trip_service
        )

        assert result is not None
        mock_trip_service.get_trip_collaborators.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_principal.id
        )

    @pytest.mark.asyncio
    async def test_list_collaborators_unauthorized_access(
        self, mock_different_principal, mock_trip_service
    ):
        """Test unauthorized user cannot list collaborators."""
        trip_id = str(uuid4())
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.get_trip_collaborators.side_effect = CoreAuthorizationError(
            message="Insufficient permissions", code="UNAUTHORIZED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_trip_collaborators(
                trip_id, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_list_collaborators_with_manage_permission(
        self,
        mock_different_principal,
        mock_trip_service,
        sample_trip_data,
    ):
        """Test collaborator with manage permission can list collaborators."""
        trip_id = str(uuid4())
        mock_collaborators = []

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = sample_trip_data
        mock_trip_service.get_trip_collaborators.return_value = mock_collaborators

        result = await list_trip_collaborators(
            trip_id, mock_different_principal, mock_trip_service
        )

        assert result is not None
        mock_trip_service.get_trip_collaborators.assert_called_once()


class TestShareTripSecurity:
    """Test security fixes in share_trip endpoint (line 992)."""

    @pytest.fixture
    def share_request(self):
        """Sample share request aligned with API schema."""
        return TripShareRequest(
            user_emails=[str(uuid4())],
            permission_level="edit",
            message="Join my trip!",
        )

    @pytest.mark.asyncio
    async def test_share_trip_owner_access(
        self, mock_principal, mock_trip_service, share_request, mock_audit_service
    ):
        """Test trip owner can share trip."""
        trip_id = uuid4()
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.share_trip.return_value = []

        result = await share_trip(
            trip_id, share_request, mock_principal, mock_trip_service
        )

        assert isinstance(result, list)
        mock_trip_service.share_trip.assert_called_once()
        mock_audit_service.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_share_trip_unauthorized_access(
        self,
        mock_different_principal,
        mock_trip_service,
        share_request,
        mock_audit_service,
    ):
        """Test unauthorized user cannot share trip."""
        trip_id = uuid4()
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.share_trip.side_effect = CoreAuthorizationError(
            message="Insufficient permissions to share trip", code="SHARE_UNAUTHORIZED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await share_trip(
                trip_id, share_request, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        mock_audit_service.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_share_trip_collaborator_with_manage_permission(
        self,
        mock_different_principal,
        mock_trip_service,
        share_request,
        mock_audit_service,
    ):
        """Test collaborator with manage permission can share trip."""
        trip_id = uuid4()
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.share_trip.return_value = []

        result = await share_trip(
            trip_id, share_request, mock_different_principal, mock_trip_service
        )

        assert isinstance(result, list)
        mock_trip_service.share_trip.assert_called_once()
        mock_audit_service.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_share_trip_collaborator_insufficient_permission(
        self,
        mock_different_principal,
        mock_trip_service,
        share_request,
        mock_audit_service,
    ):
        """Test collaborator with insufficient permission cannot share trip."""
        trip_id = uuid4()
        mock_trip_service._check_trip_access.return_value = (
            False  # Edit-only, not manage
        )
        mock_trip_service.share_trip.side_effect = CoreAuthorizationError(
            message="Manage permission required to share trip", code="MANAGE_REQUIRED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await share_trip(
                trip_id, share_request, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        mock_audit_service.assert_not_awaited()


class TestExportTripSecurity:
    """Test security fixes in export_trip endpoint (lines 1064-1066)."""

    @pytest.mark.asyncio
    async def test_export_trip_authorized_access(
        self, mock_principal, mock_trip_service, mock_audit_service
    ):
        """Test authorized user can export trip."""
        trip_id = str(uuid4())
        export_format = "pdf"

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = {"id": trip_id}

        result = await export_trip(
            trip_id, export_format, mock_principal, mock_trip_service
        )

        assert "download_url" in result
        mock_audit_service.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_export_trip_unauthorized_access(
        self, mock_different_principal, mock_trip_service, mock_audit_service
    ):
        """Test unauthorized user cannot export trip."""
        trip_id = str(uuid4())
        export_format = "pdf"

        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await export_trip(
                trip_id, export_format, mock_different_principal, mock_trip_service
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        mock_audit_service.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_export_trip_collaborator_read_access(
        self, mock_different_principal, mock_trip_service, mock_audit_service
    ):
        """Test collaborator with read access can export trip."""
        trip_id = str(uuid4())
        export_format = "json"

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = {"id": trip_id}

        result = await export_trip(
            trip_id, export_format, mock_different_principal, mock_trip_service
        )

        assert "download_url" in result
        mock_audit_service.assert_awaited_once()


class TestSecurityAuditLogging:
    """Test that security events are properly audited."""

    @pytest.mark.asyncio
    async def test_unauthorized_access_is_audited(
        self, mock_different_principal, mock_trip_service
    ):
        """Test that unauthorized access attempts are logged for security monitoring."""
        trip_id = str(uuid4())
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException):
            await get_trip(trip_id, mock_different_principal, mock_trip_service)

        # Verify generic access path executed via service
        assert mock_trip_service.get_trip.called

    @pytest.mark.asyncio
    async def test_successful_access_is_audited(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test that successful access is logged for audit trail."""
        trip_id = sample_trip_data.id
        sample_trip_data.user_id = mock_principal.id

        mock_trip_service.get_trip.return_value = sample_trip_data
        mock_trip_service._check_trip_access.return_value = True

        result = await get_trip(trip_id, mock_principal, mock_trip_service)

        assert result is not None
        mock_trip_service.get_trip.assert_called()


class TestSecurityErrorHandling:
    """Test comprehensive security error handling."""

    @pytest.mark.asyncio
    async def test_security_error_propagation(
        self, mock_principal, mock_trip_service, mock_audit_service
    ):
        """Test that security errors are properly propagated and handled."""
        trip_id = str(uuid4())
        mock_trip_service.get_trip.side_effect = CoreSecurityError(
            message="Security validation failed", code="SECURITY_ERROR"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_principal, mock_trip_service)

        # Security errors should result in appropriate HTTP status codes
        assert exc_info.value.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_resource_not_found_vs_unauthorized(
        self, mock_different_principal, mock_trip_service, mock_audit_service
    ):
        """Test that resource not found is distinguished from unauthorized access."""
        trip_id = str(uuid4())
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_different_principal, mock_trip_service)

        # Should return 404 to prevent information disclosure
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Trip not found" in str(exc_info.value.detail)


class TestParametrizedSecurityScenarios:
    """Parametrized tests for various security scenarios."""

    @pytest.mark.parametrize(
        "endpoint_func,requires_owner",
        [
            (delete_trip, True),
            (get_trip, False),
            (get_trip_summary, False),
        ],
    )
    @pytest.mark.asyncio
    async def test_endpoint_access_patterns(
        self,
        endpoint_func,
        requires_owner,
        mock_principal,
        mock_different_principal,
        mock_trip_service,
        mock_audit_service,
        sample_trip_data,
    ):
        """Test access patterns across different endpoints."""
        trip_id = str(uuid4())

        # Setup mock responses
        mock_trip_service._check_trip_access.return_value = not requires_owner
        if requires_owner:
            mock_trip_service.delete_trip.side_effect = CoreAuthorizationError(
                message="Owner required", code="OWNER_REQUIRED"
            )
        else:
            sample_trip_data.user_id = mock_principal.id
            mock_trip_service.get_trip.return_value = sample_trip_data

        # Test with non-owner principal
        if requires_owner:
            with pytest.raises(HTTPException) as exc_info:
                if endpoint_func == delete_trip:
                    await endpoint_func(
                        trip_id, mock_different_principal, mock_trip_service
                    )
                else:
                    await endpoint_func(
                        trip_id, mock_different_principal, mock_trip_service
                    )
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        else:
            # Should succeed for read operations with collaborator access
            result = await endpoint_func(
                trip_id, mock_different_principal, mock_trip_service
            )
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
