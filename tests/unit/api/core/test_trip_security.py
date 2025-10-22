"""Tests for trip access verification and security decorators.

This module tests the trip security functionality including access verification,
decorators, and integration with the existing authentication system.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status

from tripsage.api.core.trip_security import (
    TripAccessContext,
    TripAccessLevel,
    TripAccessPermission,
    check_trip_collaboration,
    check_trip_ownership,
    create_trip_access_dependency,
    get_user_trip_permissions,
    verify_trip_access,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError,
    CoreSecurityError,
)
from tripsage_core.services.business.trip_service import TripService


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
def mock_trip_service():
    """Create a mock trip service for testing."""
    service = Mock(spec=TripService)
    service.db = Mock()
    service._check_trip_access = AsyncMock()
    service.db.get_trip_by_id = AsyncMock()
    service.db.get_trip_collaborators = AsyncMock()
    return service


@pytest.fixture
def sample_trip_data():
    """Sample trip data for testing."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "title": "Test Trip",
        "visibility": "private",
        "status": "planning",
    }


class TestTripAccessContext:
    """Test TripAccessContext model validation."""

    def test_valid_context_creation(self):
        """Test creating a valid TripAccessContext."""
        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="GET /trips/123",
        )

        assert context.trip_id
        assert context.principal_id
        assert context.required_level == TripAccessLevel.READ
        assert context.operation == "GET /trips/123"
        assert context.required_permission is None

    def test_context_with_permission(self):
        """Test creating context with specific permission."""
        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.COLLABORATOR,
            required_permission=TripAccessPermission.EDIT,
            operation="PUT /trips/123",
        )

        assert context.required_permission == TripAccessPermission.EDIT

    def test_invalid_trip_id_validation(self):
        """Test validation of invalid trip IDs."""
        with pytest.raises(ValueError, match="Trip ID must be a non-empty string"):
            TripAccessContext(
                trip_id="",
                principal_id=str(uuid4()),
                required_level=TripAccessLevel.READ,
                operation="test",
            )

    def test_invalid_principal_id_validation(self):
        """Test validation of invalid principal IDs."""
        with pytest.raises(ValueError, match="Principal ID must be a non-empty string"):
            TripAccessContext(
                trip_id=str(uuid4()),
                principal_id="",
                required_level=TripAccessLevel.READ,
                operation="test",
            )


class TestVerifyTripAccess:
    """Test the core verify_trip_access function."""

    @pytest.mark.asyncio
    async def test_owner_access_granted(self, mock_trip_service, sample_trip_data):
        """Test that trip owner gets access."""
        owner_id = str(uuid4())
        sample_trip_data["user_id"] = owner_id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = []

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=owner_id,
            required_level=TripAccessLevel.OWNER,
            operation="test_owner_access",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is True
        assert result.is_owner is True
        assert result.access_level == TripAccessLevel.OWNER
        assert result.permission_granted == TripAccessPermission.MANAGE

    @pytest.mark.asyncio
    async def test_collaborator_access_granted(
        self, mock_trip_service, sample_trip_data
    ):
        """Test that trip collaborator gets appropriate access."""
        owner_id = str(uuid4())
        collaborator_id = str(uuid4())

        sample_trip_data["user_id"] = owner_id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": "edit"}
        ]

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=collaborator_id,
            required_level=TripAccessLevel.COLLABORATOR,
            operation="test_collaborator_access",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is True
        assert result.is_owner is False
        assert result.is_collaborator is True
        assert result.access_level == TripAccessLevel.COLLABORATOR
        assert result.permission_granted == TripAccessPermission.EDIT

    @pytest.mark.asyncio
    async def test_access_denied_insufficient_permission(
        self, mock_trip_service, sample_trip_data
    ):
        """Test access denial for insufficient permissions."""
        owner_id = str(uuid4())
        collaborator_id = str(uuid4())

        sample_trip_data["user_id"] = owner_id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": "view"}
        ]

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=collaborator_id,
            required_level=TripAccessLevel.COLLABORATOR,
            required_permission=TripAccessPermission.EDIT,  # Requires edit but has view
            operation="test_insufficient_permission",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is False
        assert result.denial_reason == "Operation requires edit permission"

    @pytest.mark.asyncio
    async def test_trip_not_found(self, mock_trip_service):
        """Test handling of non-existent trips."""
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = None

        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="test_not_found",
        )

        with pytest.raises(CoreResourceNotFoundError):
            await verify_trip_access(context, mock_trip_service)

    @pytest.mark.asyncio
    async def test_access_denied_by_service(self, mock_trip_service):
        """Test access denial by the underlying trip service."""
        mock_trip_service._check_trip_access.return_value = False

        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="test_service_denial",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is False
        assert "Insufficient permissions" in result.denial_reason


class TestHelperFunctions:
    """Test helper functions for trip access checking."""

    @pytest.mark.asyncio
    async def test_check_trip_ownership_true(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test check_trip_ownership returns True for owner."""
        trip_id = sample_trip_data["id"]
        mock_principal.id = sample_trip_data["user_id"]

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = []

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await check_trip_ownership(
                trip_id, mock_principal, mock_trip_service
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_trip_ownership_false(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test check_trip_ownership returns False for non-owner."""
        trip_id = sample_trip_data["id"]
        # Different user ID
        mock_principal.id = str(uuid4())

        mock_trip_service._check_trip_access.return_value = False

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await check_trip_ownership(
                trip_id, mock_principal, mock_trip_service
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_trip_collaboration_true(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test check_trip_collaboration returns True for collaborator."""
        trip_id = sample_trip_data["id"]
        collaborator_id = str(uuid4())
        mock_principal.id = collaborator_id

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": "edit"}
        ]

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await check_trip_collaboration(
                trip_id, mock_principal, mock_trip_service
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_trip_permissions_owner(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test get_user_trip_permissions for trip owner."""
        trip_id = sample_trip_data["id"]
        mock_principal.id = sample_trip_data["user_id"]

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = []

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            permissions = await get_user_trip_permissions(
                trip_id, mock_principal, mock_trip_service
            )

        assert permissions["is_authorized"] is True
        assert permissions["is_owner"] is True
        assert permissions["can_read"] is True
        assert permissions["can_edit"] is True
        assert permissions["can_manage"] is True
        assert permissions["access_level"] == "owner"
        assert permissions["permission"] == "manage"


class TestCreateTripAccessDependency:
    """Test the dependency factory function."""

    @pytest.mark.asyncio
    async def test_dependency_creation(self):
        """Test that dependency factory creates working dependency."""
        dependency = create_trip_access_dependency(TripAccessLevel.READ)

        assert callable(dependency)
        # The dependency function should be async
        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_missing_trip_id(self, mock_principal, mock_trip_service):
        """Test dependency raises HTTPException when trip_id is missing."""
        dependency = create_trip_access_dependency(TripAccessLevel.READ)

        # Mock request without trip_id in path_params
        mock_request = Mock(spec=Request)
        mock_request.path_params = {}
        mock_request.method = "GET"
        mock_request.url.path = "/trips/"
        mock_request.client = None
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing required parameter: trip_id" in str(exc_info.value.detail)


class TestAccessLevelsAndPermissions:
    """Test access level and permission enums."""

    def test_access_levels(self):
        """Test all access levels are defined correctly."""
        levels = list(TripAccessLevel)
        assert TripAccessLevel.READ in levels
        assert TripAccessLevel.WRITE in levels
        assert TripAccessLevel.OWNER in levels
        assert TripAccessLevel.COLLABORATOR in levels

        # Test string values
        assert TripAccessLevel.READ.value == "read"
        assert TripAccessLevel.WRITE.value == "write"
        assert TripAccessLevel.OWNER.value == "owner"
        assert TripAccessLevel.COLLABORATOR.value == "collaborator"

    def test_permissions(self):
        """Test all permissions are defined correctly."""
        permissions = list(TripAccessPermission)
        assert TripAccessPermission.VIEW in permissions
        assert TripAccessPermission.EDIT in permissions
        assert TripAccessPermission.MANAGE in permissions

        # Test string values
        assert TripAccessPermission.VIEW.value == "view"
        assert TripAccessPermission.EDIT.value == "edit"
        assert TripAccessPermission.MANAGE.value == "manage"


class TestErrorHandling:
    """Test error handling and security scenarios."""

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, mock_trip_service):
        """Test handling of unexpected errors during verification."""
        # Make the service method raise an unexpected error
        mock_trip_service._check_trip_access.side_effect = Exception("Database error")

        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="test_error",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            with pytest.raises(CoreSecurityError) as exc_info:
                await verify_trip_access(context, mock_trip_service)

            assert "Trip access verification failed" in str(exc_info.value)
            assert exc_info.value.code == "ACCESS_VERIFICATION_ERROR"

    @pytest.mark.asyncio
    async def test_audit_logging_on_access_denied(self, mock_trip_service):
        """Test that access denials are properly audited."""
        mock_trip_service._check_trip_access.return_value = False

        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="test_audit",
            ip_address="192.168.1.100",
            user_agent="Test Agent",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            result = await verify_trip_access(context, mock_trip_service)

            assert result.is_authorized is False
            mock_audit.assert_called_once()
            # Verify audit call contains expected information
            call_args = mock_audit.call_args[1]
            assert call_args["ip_address"] == "192.168.1.100"
            assert call_args["user_agent"] == "Test Agent"
            assert call_args["operation_type"] == "test_audit"


class TestSecurityDecoratorIntegration:
    """Test the @require_trip_access decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_creates_dependency(self):
        """Test that decorator creates proper FastAPI dependency."""
        from tripsage.api.core.trip_security import require_trip_access

        # Create a mock endpoint function
        @require_trip_access(TripAccessLevel.READ)
        async def mock_endpoint(trip_id: str, principal):
            return {"trip_id": trip_id}

        # Verify the decorator was applied
        assert hasattr(mock_endpoint, "__annotations__")
        assert "_trip_access_verification" in mock_endpoint.__annotations__

    @pytest.mark.asyncio
    async def test_dependency_extracts_trip_id_from_request(
        self, mock_principal, mock_trip_service, sample_trip_data
    ):
        """Test that dependency correctly extracts trip_id from path parameters."""
        from unittest.mock import Mock

        from fastapi import Request

        from tripsage.api.core.trip_security import create_trip_access_dependency

        # Create dependency
        dependency = create_trip_access_dependency(TripAccessLevel.READ)

        # Mock request with trip_id in path
        mock_request = Mock(spec=Request)
        mock_request.path_params = {"trip_id": sample_trip_data["id"]}
        mock_request.method = "GET"
        mock_request.url.path = f"/trips/{sample_trip_data['id']}"
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"User-Agent": "Test Client"}

        # Setup trip service
        sample_trip_data["user_id"] = mock_principal.id
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = []

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await dependency(mock_request, mock_principal, mock_trip_service)

        assert result.is_authorized is True
        assert result.is_owner is True


class TestPreConfiguredDependencies:
    """Test pre-configured dependency types."""

    def test_predefined_dependencies_exist(self):
        """Test that all predefined dependency types exist and are configured."""
        from tripsage.api.core.trip_security import (
            TripCollaboratorAccessDep,
            TripEditPermissionDep,
            TripManagePermissionDep,
            TripOwnerAccessDep,
            TripReadAccessDep,
            TripWriteAccessDep,
        )

        # All dependencies should be Annotated types
        dependencies = [
            TripReadAccessDep,
            TripWriteAccessDep,
            TripOwnerAccessDep,
            TripCollaboratorAccessDep,
            TripEditPermissionDep,
            TripManagePermissionDep,
        ]

        for dep in dependencies:
            assert hasattr(dep, "__metadata__")
            assert len(dep.__metadata__) > 0


class TestSecurityScenarios:
    """Test advanced security scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_public_trip_access_with_visibility(
        self, mock_trip_service, sample_trip_data
    ):
        """Test access to public trips by non-owners."""
        # Setup public trip
        sample_trip_data["visibility"] = "public"
        different_user_id = str(uuid4())

        mock_trip_service._check_trip_access.return_value = (
            True  # Public access allowed
        )
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = []

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=different_user_id,
            required_level=TripAccessLevel.READ,
            operation="public_trip_access",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is True
        assert result.is_owner is False
        assert result.access_level == TripAccessLevel.READ

    @pytest.mark.asyncio
    async def test_permission_hierarchy_enforcement(
        self, mock_trip_service, sample_trip_data
    ):
        """Test that permission hierarchy is properly enforced."""
        collaborator_id = str(uuid4())
        sample_trip_data["user_id"] = str(uuid4())  # Different owner

        # Setup collaborator with view permission trying to perform edit operation
        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": "view"}
        ]

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=collaborator_id,
            required_level=TripAccessLevel.COLLABORATOR,
            required_permission=TripAccessPermission.EDIT,  # Requires edit but has view
            operation="edit_attempt_with_view_permission",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is False
        assert "edit permission" in result.denial_reason

    @pytest.mark.asyncio
    async def test_multiple_collaborators_permission_check(
        self, mock_trip_service, sample_trip_data
    ):
        """Test permission checking with multiple collaborators."""
        target_collaborator_id = str(uuid4())
        other_collaborator_id = str(uuid4())

        sample_trip_data["user_id"] = str(uuid4())  # Different owner

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": other_collaborator_id, "permission": "manage"},
            {"user_id": target_collaborator_id, "permission": "edit"},
        ]

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=target_collaborator_id,
            required_level=TripAccessLevel.COLLABORATOR,
            required_permission=TripAccessPermission.EDIT,
            operation="multi_collaborator_access",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is True
        assert result.is_collaborator is True
        assert result.permission_granted == TripAccessPermission.EDIT

    @pytest.mark.parametrize(
        "permission_level,expected_access",
        [
            ("view", [TripAccessPermission.VIEW]),
            ("edit", [TripAccessPermission.VIEW, TripAccessPermission.EDIT]),
            (
                "manage",
                [
                    TripAccessPermission.VIEW,
                    TripAccessPermission.EDIT,
                    TripAccessPermission.MANAGE,
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_permission_levels_grant_appropriate_access(
        self, permission_level, expected_access, mock_trip_service, sample_trip_data
    ):
        """Test that different permission levels grant appropriate access rights."""
        collaborator_id = str(uuid4())
        sample_trip_data["user_id"] = str(uuid4())

        mock_trip_service._check_trip_access.return_value = True
        mock_trip_service.db.get_trip_by_id.return_value = sample_trip_data
        mock_trip_service.db.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": permission_level}
        ]

        context = TripAccessContext(
            trip_id=sample_trip_data["id"],
            principal_id=collaborator_id,
            required_level=TripAccessLevel.COLLABORATOR,
            operation=f"test_{permission_level}_access",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ):
            result = await verify_trip_access(context, mock_trip_service)

        assert result.is_authorized is True
        assert result.permission_granted in expected_access

    @pytest.mark.asyncio
    async def test_security_context_ip_and_user_agent_logging(self, mock_trip_service):
        """Test that IP address and user agent are captured for security logging."""
        mock_trip_service._check_trip_access.return_value = False

        context = TripAccessContext(
            trip_id=str(uuid4()),
            principal_id=str(uuid4()),
            required_level=TripAccessLevel.READ,
            operation="security_context_test",
            ip_address="203.0.113.42",
            user_agent="Mozilla/5.0 (Test Browser)",
        )

        with patch(
            "tripsage.api.core.trip_security.audit_security_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            result = await verify_trip_access(context, mock_trip_service)

            assert result.is_authorized is False
            mock_audit.assert_called_once()

            # Verify security context is properly captured
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["ip_address"] == "203.0.113.42"
            assert call_kwargs["user_agent"] == "Mozilla/5.0 (Test Browser)"
            assert call_kwargs["operation_type"] == "security_context_test"


if __name__ == "__main__":
    pytest.main([__file__])
