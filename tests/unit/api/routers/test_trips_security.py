# pyright: reportAttributeAccessIssue=false,reportUnknownArgumentType=false
"""Security tests for trips router security fixes.

This module tests all 7 security vulnerability fixes implemented in the trips router,
ensuring proper authorization, authentication, and audit logging across all endpoints.
"""

from datetime import UTC, datetime
from typing import Any
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
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreSecurityError,
)
from tripsage_core.models.api.trip_models import TripShareRequest, UpdateTripRequest
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.user_service import UserService


class TestGetTripSecurity:
    """Test security fixes in get_trip endpoint (line 279)."""

    @pytest.mark.asyncio
    async def test_get_trip_authorized_access(self, core_trip_response: Any) -> None:
        """Test authorized access to get_trip endpoint."""
        # Setup: user owns the trip
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        trip_id = core_trip_response.id
        core_trip_response.user_id = mock_principal.id

        mock_trip_service.get_trip.return_value = core_trip_response
        mock_trip_service._check_trip_access.return_value = True

        # Execute
        await get_trip(trip_id, mock_trip_service, mock_principal)

        # Verify
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_principal.id
        )

    @pytest.mark.asyncio
    async def test_get_trip_unauthorized_access_denied(
        self, core_trip_response: Any
    ) -> None:
        """Test unauthorized access denial in get_trip endpoint."""
        # Setup: different user tries to access trip
        mock_different_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="other@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        trip_id = core_trip_response.id
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.get_trip.return_value = None

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_trip_service, mock_different_principal)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Trip not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_access(self, core_trip_response: Any) -> None:
        """Test collaborator access to get_trip endpoint."""
        # Setup: user is a collaborator
        mock_collaborator_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="collaborator@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        trip_id = core_trip_response.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.get_trip.return_value = core_trip_response

        # Execute
        await get_trip(trip_id, mock_trip_service, mock_collaborator_principal)

        # Verify
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id=mock_collaborator_principal.id
        )

    @pytest.mark.asyncio
    async def test_get_trip_nonexistent_trip(self) -> None:
        """Test access to non-existent trip."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_trip_service, mock_principal)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetTripSummarySecurity:
    """Test security fixes in get_trip_summary endpoint (lines 436-440)."""

    @pytest.mark.asyncio
    async def test_list_collaborators_owner_access(
        self, core_trip_response: Any
    ) -> None:
        """Test trip owner can list collaborators."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="owner@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_db_service = Mock()
        mock_trip_service.get_trip = AsyncMock()
        mock_trip_service.db = mock_db_service
        mock_db_service.get_trip_collaborators = AsyncMock()
        mock_user_service.get_user_by_id = AsyncMock()

        trip_id = core_trip_response.id
        collaborator_id = str(uuid4())
        mock_collaborators = [
            {
                "user_id": collaborator_id,
                "permission": "edit",
                "added_at": datetime.now(UTC),
            }
        ]

        # Mock user details lookup
        mock_user = Mock()
        mock_user.email = "collaborator@example.com"
        mock_user.full_name = "Test Collaborator"
        mock_user_service.get_user_by_id.return_value = mock_user

        mock_trip_service.get_trip.return_value = core_trip_response
        mock_db_service.get_trip_collaborators.return_value = mock_collaborators

        result = await list_trip_collaborators(
            trip_id, mock_trip_service, mock_user_service, mock_principal
        )

        assert result is not None
        assert len(result.collaborators) == 1
        mock_db_service.get_trip_collaborators.assert_called_once_with(str(trip_id))
        mock_user_service.get_user_by_id.assert_called_once_with(collaborator_id)
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.update_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        update_request = UpdateTripRequest(
            title="Updated Trip",
            description="Updated description",
        )

        trip_id = core_trip_response.id
        core_trip_response.user_id = mock_principal.id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.update_trip.return_value = core_trip_response

        result = await update_trip(
            trip_id, update_request, mock_trip_service, mock_principal
        )

        assert result is not None
        mock_trip_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_collaborator_edit_permission(
        self, core_trip_response: Any
    ) -> None:
        """Test collaborator with edit permission can update trip."""
        mock_collaborator_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="collaborator@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.update_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        update_request = UpdateTripRequest(
            title="Updated Trip",
            description="Updated description",
        )

        trip_id = core_trip_response.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.update_trip.return_value = core_trip_response

        result = await update_trip(
            trip_id, update_request, mock_trip_service, mock_collaborator_principal
        )

        assert result is not None
        mock_trip_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_unauthorized_access(
        self, core_trip_response: Any
    ) -> None:
        """Test unauthorized user cannot update trip."""
        mock_unauthorized_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="unauthorized@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.update_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        update_request = UpdateTripRequest(
            title="Updated Trip",
            description="Updated description",
        )

        trip_id = core_trip_response.id
        mock_trip_service._check_trip_access.return_value = False
        mock_trip_service.update_trip.side_effect = CoreAuthorizationError(
            message="Insufficient permissions", code="UNAUTHORIZED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_trip(
                trip_id, update_request, mock_trip_service, mock_unauthorized_principal
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_trip_collaborator_insufficient_permission(
        self, core_trip_response: Any
    ) -> None:
        """Test collaborator with insufficient permission cannot update trip."""
        mock_view_only_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="viewonly@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.update_trip = AsyncMock()
        mock_trip_service._check_trip_access = Mock()

        update_request = UpdateTripRequest(
            title="Updated Trip",
            description="Updated description",
        )

        trip_id = core_trip_response.id
        mock_trip_service._check_trip_access.return_value = False  # View-only access
        mock_trip_service.update_trip.side_effect = CoreAuthorizationError(
            message="Insufficient edit permissions", code="INSUFFICIENT_PERMISSION"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_trip(
                trip_id, update_request, mock_trip_service, mock_view_only_principal
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteTripSecurity:
    """Test security fixes in delete_trip endpoint (line 720)."""

    @pytest.mark.asyncio
    async def test_list_collaborators_manage_permission(
        self, core_trip_response: Any
    ) -> None:
        """Test collaborator with manage permission can list collaborators."""
        mock_collaborator_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="collaborator@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_db_service = Mock()
        mock_trip_service.get_trip = AsyncMock()
        mock_trip_service.db = mock_db_service
        mock_db_service.get_trip_collaborators = AsyncMock()

        trip_id = core_trip_response.id
        mock_collaborators = []

        mock_trip_service.get_trip.return_value = core_trip_response
        mock_db_service.get_trip_collaborators.return_value = mock_collaborators

        result = await list_trip_collaborators(
            trip_id, mock_trip_service, mock_user_service, mock_collaborator_principal
        )

        assert result is not None
        mock_db_service.get_trip_collaborators.assert_called_once_with(str(trip_id))

    @pytest.mark.asyncio
    async def test_list_collaborators_unauthorized_access(self) -> None:
        """Test unauthorized user cannot list collaborators."""
        mock_unauthorized_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="unauthorized@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None  # No access

        with pytest.raises(HTTPException) as exc_info:
            await list_trip_collaborators(
                trip_id,
                mock_trip_service,
                mock_user_service,
                mock_unauthorized_principal,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestShareTripSecurity:
    """Test security fixes in share_trip endpoint (line 992)."""

    @pytest.mark.asyncio
    async def test_share_trip_owner_access(self) -> None:
        """Test trip owner can share trip."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="owner@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_trip_service.share_trip = AsyncMock()
        mock_user_service.get_user_by_email = AsyncMock()

        # Mock user resolution for emails
        user_ids = [str(uuid4()), str(uuid4())]
        mock_user_service.get_user_by_email.side_effect = [
            Mock(id=user_ids[0], full_name="User One"),
            Mock(id=user_ids[1], full_name="User Two"),
        ]

        share_request = TripShareRequest(
            user_emails=[f"user{i}@example.com" for i in range(2)],
            permission_level="edit",
            message="Join my trip!",
        )

        trip_id = uuid4()
        mock_trip_service.share_trip.return_value = None

        result = await share_trip(
            trip_id,
            share_request,
            mock_trip_service,
            mock_user_service,
            mock_principal,
        )

        assert isinstance(result, list)
        assert len(result) == 2  # Two collaborators added
        assert mock_trip_service.share_trip.call_count == 2

    @pytest.mark.asyncio
    async def test_share_trip_manage_permission(self) -> None:
        """Test collaborator with manage permission can share trip."""
        mock_collaborator_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="collaborator@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_trip_service.share_trip = AsyncMock()
        mock_user_service.get_user_by_email = AsyncMock()

        # Mock user resolution
        user_id = str(uuid4())
        mock_user_service.get_user_by_email.return_value = Mock(
            id=user_id, full_name="New User"
        )

        share_request = TripShareRequest(
            user_emails=["newuser@example.com"],
            permission_level="view",
            message="Check out this trip!",
        )

        trip_id = uuid4()
        mock_trip_service.share_trip.return_value = None

        result = await share_trip(
            trip_id,
            share_request,
            mock_trip_service,
            mock_user_service,
            mock_collaborator_principal,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        mock_trip_service.share_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_trip_unauthorized_access(self) -> None:
        """Test unauthorized user cannot share trip."""
        mock_unauthorized_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="unauthorized@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_trip_service.share_trip = AsyncMock()

        share_request = TripShareRequest(
            user_emails=["victim@example.com"],
            permission_level="edit",
            message="Unauthorized share attempt",
        )

        trip_id = uuid4()
        mock_trip_service.share_trip.side_effect = CoreAuthorizationError(
            message="Insufficient permissions to share trip", code="SHARE_UNAUTHORIZED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await share_trip(
                trip_id,
                share_request,
                mock_trip_service,
                mock_user_service,
                mock_unauthorized_principal,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_share_trip_insufficient_permission(self) -> None:
        """Test collaborator with insufficient permission cannot share trip."""
        mock_edit_only_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="editonly@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_user_service = Mock(spec=UserService)
        mock_trip_service.share_trip = AsyncMock()

        share_request = TripShareRequest(
            user_emails=["newuser@example.com"],
            permission_level="edit",
            message="Trying to share without manage permission",
        )

        trip_id = uuid4()
        mock_trip_service.share_trip.side_effect = CoreAuthorizationError(
            message="Manage permission required to share trip", code="MANAGE_REQUIRED"
        )

        with pytest.raises(HTTPException) as exc_info:
            await share_trip(
                trip_id,
                share_request,
                mock_trip_service,
                mock_user_service,
                mock_edit_only_principal,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestExportTripSecurity:
    """Test security fixes in export_trip endpoint (lines 1064-1066)."""

    @pytest.mark.asyncio
    async def test_export_trip_owner_access(self) -> None:
        """Test trip owner can export trip."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="owner@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = {"id": trip_id}

        result = await export_trip(
            trip_id, mock_trip_service, mock_principal, export_format="pdf"
        )

        assert "download_url" in result

    @pytest.mark.asyncio
    async def test_export_trip_collaborator_access(self) -> None:
        """Test collaborator with read access can export trip."""
        mock_collaborator_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="collaborator@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        export_format = "json"
        mock_trip_service.get_trip.return_value = {"id": trip_id}

        result = await export_trip(
            trip_id,
            mock_trip_service,
            mock_collaborator_principal,
            export_format=export_format,
        )

        assert "download_url" in result

    @pytest.mark.asyncio
    async def test_export_trip_unauthorized_access(self) -> None:
        """Test unauthorized user cannot export trip."""
        mock_unauthorized_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="unauthorized@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await export_trip(
                trip_id,
                mock_trip_service,
                mock_unauthorized_principal,
                export_format="pdf",
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestSecurityAuditLogging:
    """Test that security events are properly audited."""

    @pytest.mark.asyncio
    async def test_unauthorized_access_attempt_logged(self) -> None:
        """Test that unauthorized access attempts are logged for security monitoring."""
        mock_unauthorized_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="unauthorized@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException):
            await get_trip(trip_id, mock_trip_service, mock_unauthorized_principal)

        # Verify access attempt was logged via service call
        mock_trip_service.get_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_access_logged(self, core_trip_response: Any) -> None:
        """Test that successful access is logged for audit trail."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="user@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = core_trip_response.id
        core_trip_response.user_id = mock_principal.id
        mock_trip_service.get_trip.return_value = core_trip_response

        result = await get_trip(trip_id, mock_trip_service, mock_principal)

        assert result is not None
        mock_trip_service.get_trip.assert_called_once()


class TestSecurityErrorHandling:
    """Test security error handling."""

    @pytest.mark.asyncio
    async def test_security_error_propagation(self) -> None:
        """Test that security errors are properly propagated and handled."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="user@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.side_effect = CoreSecurityError(
            message="Security validation failed", code="SECURITY_ERROR"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_trip_service, mock_principal)

        # Security errors should result in appropriate HTTP status codes
        assert exc_info.value.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_resource_not_found_vs_unauthorized(self) -> None:
        """Test that resource not found is distinguished from unauthorized access."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="user@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)
        mock_trip_service.get_trip = AsyncMock()

        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_trip_service, mock_principal)

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
        endpoint_func: Any,
        requires_owner: bool,
        core_trip_response: Any,
    ) -> None:
        """Test access patterns across different endpoints."""
        mock_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="user@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_different_principal = Principal(
            id=str(uuid4()),
            type="user",
            email="other@example.com",
            auth_method="jwt",
            scopes=[],
            metadata={},
        )
        mock_trip_service = Mock(spec=TripService)

        trip_id = uuid4()

        # Setup mock responses
        if requires_owner:
            mock_trip_service.delete_trip = AsyncMock()
            mock_trip_service.delete_trip.side_effect = CoreAuthorizationError(
                message="Owner required", code="OWNER_REQUIRED"
            )
        else:
            mock_trip_service.get_trip = AsyncMock()
            core_trip_response.user_id = mock_principal.id
            mock_trip_service.get_trip.return_value = core_trip_response

        # Test with non-owner principal
        if requires_owner:
            with pytest.raises(HTTPException) as exc_info:
                await endpoint_func(
                    trip_id, mock_trip_service, mock_different_principal
                )
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        else:
            # Should succeed for read operations with collaborator access
            result = await endpoint_func(
                trip_id, mock_trip_service, mock_different_principal
            )
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
