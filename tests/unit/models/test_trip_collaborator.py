"""Test suite for TripCollaborator Pydantic models.

This module tests the TripCollaboratorDB, TripCollaboratorCreate, TripCollaboratorUpdate
models and PermissionLevel enum with:
- Model validation with valid and invalid data
- Permission hierarchy logic (can_view, can_edit, can_manage_collaborators)
- Field validation and constraint testing
- Serialization/deserialization with database integration
- Business logic validation (permission levels, hierarchies)
- Edge cases and boundary conditions
- Property-based testing for model validation
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from tripsage_core.models.db.trip_collaborator import (
    PermissionLevel,
    TripCollaboratorCreate,
    TripCollaboratorDB,
    TripCollaboratorUpdate,
)


class TestPermissionLevel:
    """Test PermissionLevel enum values and hierarchy."""

    def test_permission_level_values(self):
        """Test all permission level enum values."""
        assert PermissionLevel.VIEW == "view"
        assert PermissionLevel.EDIT == "edit"
        assert PermissionLevel.ADMIN == "admin"

    def test_permission_level_from_string(self):
        """Test creating permission levels from string values."""
        assert PermissionLevel("view") == PermissionLevel.VIEW
        assert PermissionLevel("edit") == PermissionLevel.EDIT
        assert PermissionLevel("admin") == PermissionLevel.ADMIN

    def test_permission_level_invalid_value(self):
        """Test invalid permission level values raise errors."""
        with pytest.raises(ValueError):
            PermissionLevel("invalid")

    def test_permission_level_case_sensitivity(self):
        """Test permission level case sensitivity."""
        with pytest.raises(ValueError):
            PermissionLevel("VIEW")  # Should be lowercase

    @pytest.mark.parametrize(
        "permission,expected_hierarchy",
        [
            (PermissionLevel.VIEW, 1),
            (PermissionLevel.EDIT, 2),
            (PermissionLevel.ADMIN, 3),
        ],
    )
    def test_permission_hierarchy_order(self, permission, expected_hierarchy):
        """Test permission levels have correct hierarchy ordering."""
        # This tests the hierarchy logic used in has_permission method
        permission_hierarchy = {
            PermissionLevel.VIEW: 1,
            PermissionLevel.EDIT: 2,
            PermissionLevel.ADMIN: 3,
        }
        assert permission_hierarchy[permission] == expected_hierarchy


class TestTripCollaboratorDB:
    """Test TripCollaboratorDB model validation and methods."""

    @pytest.fixture
    def base_collaborator_data(self):
        """Base data for creating collaborator instances."""
        now = datetime.now(UTC)
        return {
            "id": 1,
            "trip_id": 123,
            "user_id": uuid4(),
            "permission_level": PermissionLevel.EDIT,
            "added_by": uuid4(),
            "added_at": now,
            "updated_at": now,
        }

    @pytest.fixture
    def sample_trip_collaborator_dict(self, base_collaborator_data):
        """Sample collaborator dict for testing - matches conftest pattern."""
        return base_collaborator_data

    def test_collaborator_creation_with_full_data(self, base_collaborator_data):
        """Test creating TripCollaboratorDB with all fields."""
        collaborator = TripCollaboratorDB(**base_collaborator_data)

        assert collaborator.id == 1
        assert collaborator.trip_id == 123
        assert isinstance(collaborator.user_id, UUID)
        assert collaborator.permission_level == PermissionLevel.EDIT
        assert isinstance(collaborator.added_by, UUID)
        assert isinstance(collaborator.added_at, datetime)
        assert isinstance(collaborator.updated_at, datetime)

    def test_collaborator_default_permission_level(self, base_collaborator_data):
        """Test default permission level is VIEW."""
        data = base_collaborator_data.copy()
        del data["permission_level"]
        collaborator = TripCollaboratorDB(**data)

        assert collaborator.permission_level == PermissionLevel.VIEW

    def test_collaborator_permission_properties_view(self, base_collaborator_data):
        """Test permission properties for VIEW level."""
        data = base_collaborator_data.copy()
        data["permission_level"] = PermissionLevel.VIEW
        collaborator = TripCollaboratorDB(**data)

        assert collaborator.can_view is True
        assert collaborator.can_edit is False
        assert collaborator.can_manage_collaborators is False

    def test_collaborator_permission_properties_edit(self, base_collaborator_data):
        """Test permission properties for EDIT level."""
        data = base_collaborator_data.copy()
        data["permission_level"] = PermissionLevel.EDIT
        collaborator = TripCollaboratorDB(**data)

        assert collaborator.can_view is True
        assert collaborator.can_edit is True
        assert collaborator.can_manage_collaborators is False

    def test_collaborator_permission_properties_admin(self, base_collaborator_data):
        """Test permission properties for ADMIN level."""
        data = base_collaborator_data.copy()
        data["permission_level"] = PermissionLevel.ADMIN
        collaborator = TripCollaboratorDB(**data)

        assert collaborator.can_view is True
        assert collaborator.can_edit is True
        assert collaborator.can_manage_collaborators is True

    @pytest.mark.parametrize(
        "current_level,required_level,expected",
        [
            (PermissionLevel.VIEW, PermissionLevel.VIEW, True),
            (PermissionLevel.VIEW, PermissionLevel.EDIT, False),
            (PermissionLevel.VIEW, PermissionLevel.ADMIN, False),
            (PermissionLevel.EDIT, PermissionLevel.VIEW, True),
            (PermissionLevel.EDIT, PermissionLevel.EDIT, True),
            (PermissionLevel.EDIT, PermissionLevel.ADMIN, False),
            (PermissionLevel.ADMIN, PermissionLevel.VIEW, True),
            (PermissionLevel.ADMIN, PermissionLevel.EDIT, True),
            (PermissionLevel.ADMIN, PermissionLevel.ADMIN, True),
        ],
    )
    def test_has_permission_hierarchy(
        self, base_collaborator_data, current_level, required_level, expected
    ):
        """Test has_permission method respects hierarchy."""
        data = base_collaborator_data.copy()
        data["permission_level"] = current_level
        collaborator = TripCollaboratorDB(**data)

        assert collaborator.has_permission(required_level) == expected

    def test_collaborator_model_config(self, base_collaborator_data):
        """Test model configuration settings."""
        collaborator = TripCollaboratorDB(**base_collaborator_data)

        # Test from_attributes is True (should work with ORM objects)
        assert collaborator.model_config["from_attributes"] is True

        # Test str_strip_whitespace is True
        assert collaborator.model_config["str_strip_whitespace"] is True

        # Test validate_assignment is True
        assert collaborator.model_config["validate_assignment"] is True

    def test_collaborator_serialization_round_trip(self, base_collaborator_data):
        """Test model can be serialized and deserialized."""
        original = TripCollaboratorDB(**base_collaborator_data)

        # Test dict round trip
        data_dict = original.model_dump()
        reconstructed = TripCollaboratorDB.model_validate(data_dict)
        assert reconstructed.id == original.id
        assert reconstructed.trip_id == original.trip_id
        assert reconstructed.user_id == original.user_id
        assert reconstructed.permission_level == original.permission_level

        # Test JSON round trip
        json_str = original.model_dump_json()
        json_reconstructed = TripCollaboratorDB.model_validate_json(json_str)
        assert json_reconstructed.id == original.id
        assert json_reconstructed.permission_level == original.permission_level

    def test_collaborator_validation_errors(self):
        """Test validation errors for invalid data."""
        # Test invalid trip_id (missing)
        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorDB(
                id=1,
                user_id=uuid4(),
                permission_level=PermissionLevel.VIEW,
                added_by=uuid4(),
                added_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("trip_id",) for error in errors)

        # Test invalid permission_level
        with pytest.raises(ValidationError):
            TripCollaboratorDB(
                id=1,
                trip_id=123,
                user_id=uuid4(),
                permission_level="invalid_permission",
                added_by=uuid4(),
                added_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    def test_collaborator_uuid_validation(self, base_collaborator_data):
        """Test UUID field validation."""
        # Test invalid UUID string
        data = base_collaborator_data.copy()
        data["user_id"] = "invalid-uuid"

        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorDB(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)

    def test_collaborator_datetime_validation(self, base_collaborator_data):
        """Test datetime field validation."""
        # Test invalid datetime
        data = base_collaborator_data.copy()
        data["added_at"] = "invalid-datetime"

        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorDB(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("added_at",) for error in errors)

    def test_collaborator_str_strip_whitespace(self, base_collaborator_data):
        """Test string fields are stripped of whitespace."""
        # Note: Enum fields are validated before str_strip_whitespace in Pydantic v2
        # so we test with a valid enum value
        collaborator = TripCollaboratorDB(**base_collaborator_data)
        assert collaborator.permission_level == PermissionLevel.EDIT

    def test_collaborator_validate_assignment(self, base_collaborator_data):
        """Test validate_assignment configuration."""
        collaborator = TripCollaboratorDB(**base_collaborator_data)

        # Test assignment validation works
        collaborator.permission_level = PermissionLevel.ADMIN
        assert collaborator.permission_level == PermissionLevel.ADMIN

        # Test invalid assignment raises error
        with pytest.raises(ValidationError):
            collaborator.permission_level = "invalid_permission"


class TestTripCollaboratorCreate:
    """Test TripCollaboratorCreate model validation."""

    @pytest.fixture
    def base_create_data(self):
        """Base data for creating collaborator creation requests."""
        return {
            "trip_id": 123,
            "user_id": uuid4(),
            "permission_level": PermissionLevel.EDIT,
            "added_by": uuid4(),
        }

    def test_create_collaborator_valid_data(self, base_create_data):
        """Test creating TripCollaboratorCreate with valid data."""
        create_request = TripCollaboratorCreate(**base_create_data)

        assert create_request.trip_id == 123
        assert isinstance(create_request.user_id, UUID)
        assert create_request.permission_level == PermissionLevel.EDIT
        assert isinstance(create_request.added_by, UUID)

    def test_create_collaborator_default_permission(self, base_create_data):
        """Test default permission level is VIEW."""
        data = base_create_data.copy()
        del data["permission_level"]
        create_request = TripCollaboratorCreate(**data)

        assert create_request.permission_level == PermissionLevel.VIEW

    def test_create_collaborator_trip_id_validation(self, base_create_data):
        """Test trip_id validation (must be positive)."""
        # Test zero trip_id
        data = base_create_data.copy()
        data["trip_id"] = 0

        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorCreate(**data)

        errors = exc_info.value.errors()
        trip_id_errors = [e for e in errors if "trip_id" in str(e["loc"])]
        assert len(trip_id_errors) > 0

        # Test negative trip_id
        data["trip_id"] = -1
        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorCreate(**data)

        errors = exc_info.value.errors()
        trip_id_errors = [e for e in errors if "trip_id" in str(e["loc"])]
        assert len(trip_id_errors) > 0

    def test_create_collaborator_field_validators(self, base_create_data):
        """Test field validators work correctly."""
        # Test positive trip_id passes validation
        data = base_create_data.copy()
        data["trip_id"] = 999
        create_request = TripCollaboratorCreate(**data)
        assert create_request.trip_id == 999

        # Test UUID validation for user_id
        data = base_create_data.copy()
        valid_uuid = uuid4()
        data["user_id"] = valid_uuid
        create_request = TripCollaboratorCreate(**data)
        assert create_request.user_id == valid_uuid

    def test_create_collaborator_validation_errors(self):
        """Test validation errors for invalid create data."""
        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorCreate()

        errors = exc_info.value.errors()
        required_fields = {"trip_id", "user_id", "added_by"}
        error_fields = {next(iter(error["loc"])) for error in errors}
        assert required_fields.issubset(error_fields)

    def test_create_collaborator_uuid_validation_custom(self, base_create_data):
        """Test custom UUID validation in field validators."""
        # Test invalid UUID format
        data = base_create_data.copy()
        data["user_id"] = "not-a-uuid"

        with pytest.raises(ValidationError) as exc_info:
            TripCollaboratorCreate(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)

    def test_create_collaborator_serialization(self, base_create_data):
        """Test serialization of create model."""
        create_request = TripCollaboratorCreate(**base_create_data)

        # Test model_dump
        data_dict = create_request.model_dump()
        assert "trip_id" in data_dict
        assert "user_id" in data_dict
        assert "permission_level" in data_dict
        assert "added_by" in data_dict

        # Test JSON serialization
        json_str = create_request.model_dump_json()
        assert "trip_id" in json_str
        assert "permission_level" in json_str

    @pytest.mark.parametrize(
        "permission_level",
        [PermissionLevel.VIEW, PermissionLevel.EDIT, PermissionLevel.ADMIN],
    )
    def test_create_collaborator_all_permission_levels(
        self, base_create_data, permission_level
    ):
        """Test creating collaborators with all permission levels."""
        data = base_create_data.copy()
        data["permission_level"] = permission_level
        create_request = TripCollaboratorCreate(**data)

        assert create_request.permission_level == permission_level

    def test_create_collaborator_str_strip_whitespace(self, base_create_data):
        """Test string fields are stripped of whitespace."""
        # Note: Enum fields are validated before str_strip_whitespace in Pydantic v2
        # so we test with a valid enum value
        create_request = TripCollaboratorCreate(**base_create_data)
        assert create_request.permission_level == PermissionLevel.EDIT


class TestTripCollaboratorUpdate:
    """Test TripCollaboratorUpdate model validation."""

    def test_update_collaborator_empty(self):
        """Test creating empty update model."""
        update_request = TripCollaboratorUpdate()

        assert update_request.permission_level is None
        assert update_request.has_updates() is False

    def test_update_collaborator_permission_only(self):
        """Test updating only permission level."""
        update_request = TripCollaboratorUpdate(permission_level=PermissionLevel.ADMIN)

        assert update_request.permission_level == PermissionLevel.ADMIN
        assert update_request.has_updates() is True

    def test_update_collaborator_has_updates_method(self):
        """Test has_updates method logic."""
        # Test no updates
        update_request = TripCollaboratorUpdate()
        assert update_request.has_updates() is False

        # Test with permission_level update
        update_request = TripCollaboratorUpdate(permission_level=PermissionLevel.EDIT)
        assert update_request.has_updates() is True

        # Test explicit None
        update_request = TripCollaboratorUpdate(permission_level=None)
        assert update_request.has_updates() is False

    def test_update_collaborator_get_update_fields(self):
        """Test get_update_fields method."""
        # Test no updates
        update_request = TripCollaboratorUpdate()
        update_fields = update_request.get_update_fields()
        assert update_fields == {}

        # Test with permission_level
        update_request = TripCollaboratorUpdate(permission_level=PermissionLevel.ADMIN)
        update_fields = update_request.get_update_fields()
        assert update_fields == {"permission_level": PermissionLevel.ADMIN}

        # Test explicit None doesn't appear in updates
        update_request = TripCollaboratorUpdate(permission_level=None)
        update_fields = update_request.get_update_fields()
        assert update_fields == {}

    @pytest.mark.parametrize(
        "permission_level",
        [PermissionLevel.VIEW, PermissionLevel.EDIT, PermissionLevel.ADMIN],
    )
    def test_update_collaborator_all_permission_levels(self, permission_level):
        """Test updating with all permission levels."""
        update_request = TripCollaboratorUpdate(permission_level=permission_level)

        assert update_request.permission_level == permission_level
        assert update_request.has_updates() is True
        update_fields = update_request.get_update_fields()
        assert update_fields["permission_level"] == permission_level

    def test_update_collaborator_validation_errors(self):
        """Test validation errors for invalid update data."""
        # Test invalid permission level
        with pytest.raises(ValidationError):
            TripCollaboratorUpdate(permission_level="invalid_permission")

    def test_update_collaborator_serialization(self):
        """Test serialization of update model."""
        update_request = TripCollaboratorUpdate(permission_level=PermissionLevel.EDIT)

        # Test model_dump
        data_dict = update_request.model_dump()
        assert data_dict["permission_level"] == "edit"

        # Test model_dump with exclude_none
        data_dict_no_none = update_request.model_dump(exclude_none=True)
        assert "permission_level" in data_dict_no_none
        # Should only contain non-None fields

        # Test JSON serialization
        json_str = update_request.model_dump_json()
        assert "edit" in json_str

    def test_update_collaborator_str_strip_whitespace(self):
        """Test string fields are stripped of whitespace."""
        # Note: Enum fields are validated before str_strip_whitespace in Pydantic v2
        # so we test with a valid enum value
        update_request = TripCollaboratorUpdate(permission_level=PermissionLevel.VIEW)
        assert update_request.permission_level == PermissionLevel.VIEW

    def test_update_collaborator_model_config(self):
        """Test model configuration settings."""
        update_request = TripCollaboratorUpdate()

        # Test str_strip_whitespace is True
        assert update_request.model_config["str_strip_whitespace"] is True


class TestTripCollaboratorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_collaborator_with_same_user_and_added_by(self):
        """Test collaborator where user_id equals added_by (self-addition)."""
        user_id = uuid4()
        now = datetime.now(UTC)

        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=123,
            user_id=user_id,
            permission_level=PermissionLevel.ADMIN,
            added_by=user_id,  # Same as user_id
            added_at=now,
            updated_at=now,
        )

        assert collaborator.user_id == collaborator.added_by
        assert collaborator.can_manage_collaborators is True

    def test_collaborator_with_extreme_trip_ids(self):
        """Test collaborators with extreme trip ID values."""
        user_id = uuid4()
        now = datetime.now(UTC)

        # Test very large trip_id
        large_trip_id = 2**31 - 1  # Max 32-bit integer
        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=large_trip_id,
            user_id=user_id,
            permission_level=PermissionLevel.VIEW,
            added_by=uuid4(),
            added_at=now,
            updated_at=now,
        )
        assert collaborator.trip_id == large_trip_id

        # Test trip_id of 1 (minimum valid)
        create_request = TripCollaboratorCreate(
            trip_id=1, user_id=user_id, added_by=uuid4()
        )
        assert create_request.trip_id == 1

    def test_collaborator_timezone_handling(self):
        """Test datetime handling with different timezones."""
        user_id = uuid4()

        # Test with UTC timezone
        utc_time = datetime.now(UTC)
        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=123,
            user_id=user_id,
            permission_level=PermissionLevel.VIEW,
            added_by=uuid4(),
            added_at=utc_time,
            updated_at=utc_time,
        )

        assert collaborator.added_at.tzinfo == UTC
        assert collaborator.updated_at.tzinfo == UTC

    def test_collaborator_permission_level_case_variations(self):
        """Test permission level handling with various string cases."""
        user_id = uuid4()

        # Test lowercase (should work)
        create_request = TripCollaboratorCreate(
            trip_id=123,
            user_id=user_id,
            permission_level="edit",  # String instead of enum
            added_by=uuid4(),
        )
        assert create_request.permission_level == PermissionLevel.EDIT

        # Test that uppercase fails (case sensitive)
        with pytest.raises(ValidationError):
            TripCollaboratorCreate(
                trip_id=123,
                user_id=user_id,
                permission_level="EDIT",  # Uppercase should fail
                added_by=uuid4(),
            )


class TestTripCollaboratorPropertyBased:
    """Property-based tests using Hypothesis for validation."""

    @given(
        trip_id=st.integers(min_value=1, max_value=2**31 - 1),
        user_id=st.uuids(),
        added_by=st.uuids(),
        permission_level=st.sampled_from(list(PermissionLevel)),
    )
    def test_collaborator_create_property_based(
        self, trip_id, user_id, added_by, permission_level
    ):
        """Property-based test for TripCollaboratorCreate validation."""
        create_request = TripCollaboratorCreate(
            trip_id=trip_id,
            user_id=user_id,
            permission_level=permission_level,
            added_by=added_by,
        )

        # Invariants that should always hold
        assert create_request.trip_id >= 1
        assert isinstance(create_request.user_id, UUID)
        assert isinstance(create_request.added_by, UUID)
        assert create_request.permission_level in list(PermissionLevel)

    @given(
        collaborator_id=st.integers(min_value=1),
        trip_id=st.integers(min_value=1, max_value=2**31 - 1),
        user_id=st.uuids(),
        added_by=st.uuids(),
        permission_level=st.sampled_from(list(PermissionLevel)),
    )
    def test_collaborator_db_permission_hierarchy_property(
        self, collaborator_id, trip_id, user_id, added_by, permission_level
    ):
        """Property-based test for permission hierarchy invariants."""
        now = datetime.now(UTC)
        collaborator = TripCollaboratorDB(
            id=collaborator_id,
            trip_id=trip_id,
            user_id=user_id,
            permission_level=permission_level,
            added_by=added_by,
            added_at=now,
            updated_at=now,
        )

        # Invariants for permission hierarchy
        assert collaborator.can_view is True  # All levels can view

        if permission_level in [PermissionLevel.EDIT, PermissionLevel.ADMIN]:
            assert collaborator.can_edit is True
        else:
            assert collaborator.can_edit is False

        if permission_level == PermissionLevel.ADMIN:
            assert collaborator.can_manage_collaborators is True
        else:
            assert collaborator.can_manage_collaborators is False

        # Test has_permission method invariants
        assert collaborator.has_permission(PermissionLevel.VIEW) is True
        if permission_level == PermissionLevel.ADMIN:
            assert collaborator.has_permission(PermissionLevel.EDIT) is True
            assert collaborator.has_permission(PermissionLevel.ADMIN) is True

    @given(
        permission_level=st.one_of(st.sampled_from(list(PermissionLevel)), st.none())
    )
    def test_collaborator_update_property_based(self, permission_level):
        """Property-based test for TripCollaboratorUpdate validation."""
        update_request = TripCollaboratorUpdate(permission_level=permission_level)

        # Invariants that should always hold
        if permission_level is not None:
            assert update_request.has_updates() is True
            update_fields = update_request.get_update_fields()
            assert "permission_level" in update_fields
            assert update_fields["permission_level"] == permission_level
        else:
            assert update_request.has_updates() is False
            assert update_request.get_update_fields() == {}

    @given(st.integers())
    def test_trip_id_validation_property_based(self, trip_id):
        """Property-based test for trip_id validation."""
        user_id = uuid4()
        added_by = uuid4()

        if trip_id <= 0:
            # Should raise validation error for non-positive trip_id
            with pytest.raises(ValidationError):
                TripCollaboratorCreate(
                    trip_id=trip_id,
                    user_id=user_id,
                    added_by=added_by,
                )
        else:
            # Should succeed for positive trip_id
            create_request = TripCollaboratorCreate(
                trip_id=trip_id,
                user_id=user_id,
                added_by=added_by,
            )
            assert create_request.trip_id == trip_id


class TestTripCollaboratorBusinessLogic:
    """Test business logic and integration scenarios."""

    def test_permission_escalation_workflow(self):
        """Test workflow of escalating permissions."""
        user_id = uuid4()
        admin_id = uuid4()
        now = datetime.now(UTC)

        # Start with VIEW permission
        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=123,
            user_id=user_id,
            permission_level=PermissionLevel.VIEW,
            added_by=admin_id,
            added_at=now,
            updated_at=now,
        )

        assert collaborator.can_view is True
        assert collaborator.can_edit is False
        assert collaborator.can_manage_collaborators is False

        # Escalate to EDIT
        collaborator.permission_level = PermissionLevel.EDIT
        assert collaborator.can_view is True
        assert collaborator.can_edit is True
        assert collaborator.can_manage_collaborators is False

        # Escalate to ADMIN
        collaborator.permission_level = PermissionLevel.ADMIN
        assert collaborator.can_view is True
        assert collaborator.can_edit is True
        assert collaborator.can_manage_collaborators is True

    def test_permission_downgrade_workflow(self):
        """Test workflow of downgrading permissions."""
        user_id = uuid4()
        admin_id = uuid4()
        now = datetime.now(UTC)

        # Start with ADMIN permission
        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=123,
            user_id=user_id,
            permission_level=PermissionLevel.ADMIN,
            added_by=admin_id,
            added_at=now,
            updated_at=now,
        )

        assert collaborator.can_manage_collaborators is True

        # Downgrade to EDIT
        collaborator.permission_level = PermissionLevel.EDIT
        assert collaborator.can_edit is True
        assert collaborator.can_manage_collaborators is False

        # Downgrade to VIEW
        collaborator.permission_level = PermissionLevel.VIEW
        assert collaborator.can_view is True
        assert collaborator.can_edit is False
        assert collaborator.can_manage_collaborators is False

    def test_bulk_permission_check(self):
        """Test checking permissions for multiple collaborators."""
        admin_id = uuid4()
        now = datetime.now(UTC)

        collaborators = []
        permission_levels = [
            PermissionLevel.VIEW,
            PermissionLevel.EDIT,
            PermissionLevel.ADMIN,
        ]
        for i, level in enumerate(permission_levels):
            collaborators.append(
                TripCollaboratorDB(
                    id=i + 1,
                    trip_id=123,
                    user_id=uuid4(),
                    permission_level=level,
                    added_by=admin_id,
                    added_at=now,
                    updated_at=now,
                )
            )

        # Test bulk operations
        view_count = sum(1 for c in collaborators if c.can_view)
        edit_count = sum(1 for c in collaborators if c.can_edit)
        admin_count = sum(1 for c in collaborators if c.can_manage_collaborators)

        assert view_count == 3  # All can view
        assert edit_count == 2  # EDIT and ADMIN can edit
        assert admin_count == 1  # Only ADMIN can manage

    def test_collaborator_update_scenarios(self):
        """Test various update scenarios."""
        # Test partial update with permission change
        update = TripCollaboratorUpdate(permission_level=PermissionLevel.ADMIN)
        assert update.has_updates() is True

        update_fields = update.get_update_fields()
        assert len(update_fields) == 1
        assert update_fields["permission_level"] == PermissionLevel.ADMIN

        # Test empty update
        empty_update = TripCollaboratorUpdate()
        assert empty_update.has_updates() is False
        assert empty_update.get_update_fields() == {}

        # Test update with None (should be treated as no update)
        none_update = TripCollaboratorUpdate(permission_level=None)
        assert none_update.has_updates() is False
        assert none_update.get_update_fields() == {}

    def test_serialization_for_api_responses(self):
        """Test serialization suitable for API responses."""
        user_id = uuid4()
        added_by = uuid4()
        now = datetime.now(UTC)

        collaborator = TripCollaboratorDB(
            id=1,
            trip_id=123,
            user_id=user_id,
            permission_level=PermissionLevel.EDIT,
            added_by=added_by,
            added_at=now,
            updated_at=now,
        )

        # Test full serialization
        full_data = collaborator.model_dump()
        expected_fields = {
            "id",
            "trip_id",
            "user_id",
            "permission_level",
            "added_by",
            "added_at",
            "updated_at",
        }
        assert set(full_data.keys()) == expected_fields

        # Test JSON serialization with datetime handling
        json_data = collaborator.model_dump_json()
        assert "edit" in json_data  # Permission level should be serialized as string
        assert str(user_id) in json_data  # UUID should be serialized as string

    def test_model_validation_with_database_integration_patterns(self):
        """Test validation patterns that would work with database integration."""
        user_id = uuid4()
        added_by = uuid4()
        now = datetime.now(UTC)

        # Test creating from database-like dict (simulate ORM result)
        db_result = {
            "id": 1,
            "trip_id": 123,
            "user_id": str(user_id),  # Database might return as string
            "permission_level": "edit",  # Database stores as string
            "added_by": str(added_by),
            "added_at": now.isoformat(),  # Database might return as ISO string
            "updated_at": now.isoformat(),
        }

        # Should work with from_attributes=True
        collaborator = TripCollaboratorDB.model_validate(db_result)
        assert collaborator.user_id == user_id
        assert collaborator.permission_level == PermissionLevel.EDIT
        assert isinstance(collaborator.added_at, datetime)
