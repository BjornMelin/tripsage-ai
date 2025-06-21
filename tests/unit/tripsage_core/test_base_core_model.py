"""
Tests for TripSage Core base model classes.

This module tests the centralized base model classes that provide
the foundation for all TripSage models.
"""

import pytest
from pydantic import Field, ValidationError

from tripsage_core.models.base_core_model import (
    TripSageBaseResponse,
    TripSageDBModel,
    TripSageDomainModel,
    TripSageModel,
)


class TestTripSageModel:
    """Tests for the base TripSageModel class."""

    def test_basic_model_creation(self):
        """Test basic TripSageModel creation."""

        class TestModel(TripSageModel):
            name: str
            value: int = 42

        model = TestModel(name="test")
        assert model.name == "test"
        assert model.value == 42

    def test_populate_by_name(self):
        """Test populate_by_name configuration."""

        class TestModel(TripSageModel):
            full_name: str = Field(alias="name")

        # Should work with both field name and alias
        model1 = TestModel(full_name="John Doe")
        model2 = TestModel(name="Jane Doe")

        assert model1.full_name == "John Doe"
        assert model2.full_name == "Jane Doe"

    def test_validate_assignment(self):
        """Test validate_assignment configuration."""

        class TestModel(TripSageModel):
            value: int

        model = TestModel(value=10)
        assert model.value == 10

        # Assignment validation should work
        model.value = 20
        assert model.value == 20

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            model.value = "invalid"

    def test_extra_ignore(self):
        """Test extra='ignore' configuration."""

        class TestModel(TripSageModel):
            name: str

        # Extra fields should be ignored, not raise error
        model = TestModel(name="test", extra_field="ignored")
        assert model.name == "test"
        assert not hasattr(model, "extra_field")

    def test_inheritance(self):
        """Test model inheritance from TripSageModel."""

        class BaseModel(TripSageModel):
            base_field: str

        class ChildModel(BaseModel):
            child_field: int

        model = ChildModel(base_field="base", child_field=42)
        assert model.base_field == "base"
        assert model.child_field == 42
        assert isinstance(model, TripSageModel)
        assert isinstance(model, BaseModel)


class TestTripSageBaseResponse:
    """Tests for the TripSageBaseResponse class."""

    def test_basic_response_creation(self):
        """Test basic TripSageBaseResponse creation."""

        class TestResponse(TripSageBaseResponse):
            success: bool = True
            data: str = "test data"

        response = TestResponse()
        assert response.success is True
        assert response.data == "test data"

    def test_extra_allow(self):
        """Test extra='allow' configuration for responses."""

        class TestResponse(TripSageBaseResponse):
            message: str

        # Extra fields should be allowed for API compatibility
        response = TestResponse(message="success", extra_field="this should be allowed", api_version="2.0")

        assert response.message == "success"
        # Extra fields should be accessible
        assert hasattr(response, "extra_field")
        assert response.extra_field == "this should be allowed"
        assert hasattr(response, "api_version")
        assert response.api_version == "2.0"

    def test_inheritance_from_tripsage_model(self):
        """Test that TripSageBaseResponse inherits from TripSageModel."""

        class TestResponse(TripSageBaseResponse):
            status: str

        response = TestResponse(status="ok")
        assert isinstance(response, TripSageModel)
        assert isinstance(response, TripSageBaseResponse)

    def test_populate_by_name_in_response(self):
        """Test populate_by_name works in response models."""

        class TestResponse(TripSageBaseResponse):
            status_code: int = Field(alias="status")

        response1 = TestResponse(status_code=200)
        response2 = TestResponse(status=404)

        assert response1.status_code == 200
        assert response2.status_code == 404


class TestTripSageDomainModel:
    """Tests for the TripSageDomainModel class."""

    def test_basic_domain_model(self):
        """Test basic TripSageDomainModel creation."""

        class TestDomainModel(TripSageDomainModel):
            entity_id: str
            entity_type: str

        model = TestDomainModel(entity_id="test-123", entity_type="accommodation")

        assert model.entity_id == "test-123"
        assert model.entity_type == "accommodation"

    def test_inheritance_from_tripsage_model(self):
        """Test that TripSageDomainModel inherits from TripSageModel."""

        class TestDomainModel(TripSageDomainModel):
            name: str

        model = TestDomainModel(name="test")
        assert isinstance(model, TripSageModel)
        assert isinstance(model, TripSageDomainModel)

    def test_extra_ignore_in_domain(self):
        """Test extra='ignore' in domain models."""

        class TestDomainModel(TripSageDomainModel):
            name: str

        # Domain models should ignore extra fields for clean domain logic
        model = TestDomainModel(name="test", extra_field="ignored")
        assert model.name == "test"
        assert not hasattr(model, "extra_field")

    def test_domain_model_validation(self):
        """Test validation in domain models."""

        class TestDomainModel(TripSageDomainModel):
            price: float = Field(gt=0)
            currency: str = Field(min_length=3, max_length=3)

        # Valid model
        model = TestDomainModel(price=100.0, currency="USD")
        assert model.price == 100.0
        assert model.currency == "USD"

        # Invalid price
        with pytest.raises(ValidationError):
            TestDomainModel(price=-10.0, currency="USD")

        # Invalid currency length
        with pytest.raises(ValidationError):
            TestDomainModel(price=100.0, currency="INVALID")


class TestTripSageDBModel:
    """Tests for the TripSageDBModel class."""

    def test_basic_db_model(self):
        """Test basic TripSageDBModel creation."""

        class TestDBModel(TripSageDBModel):
            id: int
            name: str

        model = TestDBModel(id=1, name="test")
        assert model.id == 1
        assert model.name == "test"

    def test_inheritance_from_tripsage_model(self):
        """Test that TripSageDBModel inherits from TripSageModel."""

        class TestDBModel(TripSageDBModel):
            name: str

        model = TestDBModel(name="test")
        assert isinstance(model, TripSageModel)
        assert isinstance(model, TripSageDBModel)

    def test_from_attributes_configuration(self):
        """Test from_attributes=True configuration for ORM compatibility."""

        class TestDBModel(TripSageDBModel):
            id: int
            name: str

        # Simulate SQLAlchemy-like object
        class MockORM:
            def __init__(self):
                self.id = 42
                self.name = "ORM Object"

        orm_obj = MockORM()

        # Should work with from_attributes=True
        model = TestDBModel.model_validate(orm_obj)
        assert model.id == 42
        assert model.name == "ORM Object"

    def test_extra_ignore_in_db_model(self):
        """Test extra='ignore' in database models."""

        class TestDBModel(TripSageDBModel):
            name: str

        # DB models should ignore extra fields for clean data modeling
        model = TestDBModel(name="test", extra_field="ignored")
        assert model.name == "test"
        assert not hasattr(model, "extra_field")


class TestModelInteraction:
    """Tests for interaction between different model types."""

    def test_model_hierarchy(self):
        """Test the model inheritance hierarchy."""

        class DomainModel(TripSageDomainModel):
            name: str

        class DBModel(TripSageDBModel):
            name: str

        class ResponseModel(TripSageBaseResponse):
            name: str

        domain = DomainModel(name="domain")
        db = DBModel(name="db")
        response = ResponseModel(name="response")

        # All should inherit from TripSageModel
        assert isinstance(domain, TripSageModel)
        assert isinstance(db, TripSageModel)
        assert isinstance(response, TripSageModel)

        # But should be distinct types
        assert type(domain) is not type(db)
        assert type(db) is not type(response)
        assert type(domain) is not type(response)

    def test_model_config_inheritance(self):
        """Test that model configuration is properly inherited."""

        class TestDomain(TripSageDomainModel):
            value: int

        class TestDB(TripSageDBModel):
            value: int

        class TestResponse(TripSageBaseResponse):
            value: int

        # All should have validate_assignment=True
        domain = TestDomain(value=1)
        db = TestDB(value=1)
        response = TestResponse(value=1)

        # Test assignment validation works
        domain.value = 2
        db.value = 2
        response.value = 2

        assert domain.value == 2
        assert db.value == 2
        assert response.value == 2

        # Invalid assignments should fail
        with pytest.raises(ValidationError):
            domain.value = "invalid"
        with pytest.raises(ValidationError):
            db.value = "invalid"
        with pytest.raises(ValidationError):
            response.value = "invalid"

    def test_cross_model_data_flow(self):
        """Test converting data between different model types."""

        class DomainUser(TripSageDomainModel):
            name: str
            email: str

        class DBUser(TripSageDBModel):
            id: int
            name: str
            email: str

        class UserResponse(TripSageBaseResponse):
            id: int
            name: str
            email: str
            success: bool = True

        # Start with domain model
        domain_user = DomainUser(name="John Doe", email="john@example.com")

        # Convert to DB model (adding ID)
        db_user = DBUser(id=123, name=domain_user.name, email=domain_user.email)

        # Convert to response model
        response = UserResponse(id=db_user.id, name=db_user.name, email=db_user.email)

        assert domain_user.name == db_user.name == response.name
        assert domain_user.email == db_user.email == response.email
        assert db_user.id == response.id == 123
        assert response.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
