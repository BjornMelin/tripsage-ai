"""
Basic tests for TripSage Core domain models using modern Pydantic v2 patterns.

This test module follows latest best practices from 2024:
- Tests actual domain models that exist in the codebase
- Pydantic v2 field validators and model validation
- Modern pytest fixtures and parameterization
- Focused on core functionality that exists
"""

import pytest
from pydantic import ValidationError

from tripsage_core.models.domain.accommodation import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
)
from tripsage_core.models.domain.flight import (
    Airport,
    CabinClass,
    FlightOffer,
    FlightSegment,
)
from tripsage_core.models.domain.memory import (
    Entity,
    Relation,
)
from tripsage_core.models.schemas_common.enums import AccommodationType


class TestAccommodationDomainModels:
    """Test suite for accommodation-related domain models."""

    def test_accommodation_location_creation_success(self):
        """Test successful creation of accommodation location."""
        location = AccommodationLocation(
            city="New York",
            country="United States",
            address="123 Main St",
            postal_code="10001",
            latitude=40.7128,
            longitude=-74.0060,
        )

        assert location.city == "New York"
        assert location.country == "United States"
        assert location.address == "123 Main St"
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060

    def test_accommodation_location_required_fields(self):
        """Test that required fields are validated."""
        # Should work with just required fields
        location = AccommodationLocation(
            city="Paris",
            country="France",
        )
        assert location.city == "Paris"
        assert location.country == "France"

        # Should fail without required fields
        with pytest.raises(ValidationError):
            AccommodationLocation()

    def test_accommodation_amenity_creation_success(self):
        """Test successful creation of accommodation amenity."""
        amenity = AccommodationAmenity(
            name="Free WiFi",
            category="Internet",
            description="Complimentary high-speed internet access",
        )

        assert amenity.name == "Free WiFi"
        assert amenity.category == "Internet"
        assert amenity.description == "Complimentary high-speed internet access"

    def test_accommodation_image_creation_success(self):
        """Test successful creation of accommodation image."""
        image = AccommodationImage(
            url="https://example.com/image.jpg",
            caption="Beautiful hotel room",
            is_primary=True,
        )

        assert image.url == "https://example.com/image.jpg"
        assert image.caption == "Beautiful hotel room"
        assert image.is_primary is True

    def test_accommodation_listing_creation_success(self):
        """Test successful creation of accommodation listing."""
        location = AccommodationLocation(
            city="New York",
            country="United States",
        )

        listing = AccommodationListing(
            id="acc-123",
            name="Luxury Hotel NYC",
            property_type=AccommodationType.HOTEL,
            location=location,
            price_per_night=299.99,
            currency="USD",
            max_guests=4,
            rating=4.7,
            review_count=1524,
        )

        assert listing.id == "acc-123"
        assert listing.name == "Luxury Hotel NYC"
        assert listing.property_type == AccommodationType.HOTEL
        assert listing.price_per_night == 299.99
        assert listing.currency == "USD"
        assert listing.max_guests == 4
        assert listing.rating == 4.7

    def test_accommodation_listing_serialization(self):
        """Test accommodation listing serialization."""
        location = AccommodationLocation(city="Paris", country="France")
        listing = AccommodationListing(
            id="acc-456",
            name="Paris Apartment",
            property_type=AccommodationType.APARTMENT,
            location=location,
            price_per_night=150.0,
            currency="EUR",
            max_guests=2,
        )

        # Test model_dump
        data = listing.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "Paris Apartment"
        assert data["location"]["city"] == "Paris"

        # Test model_dump_json
        json_str = listing.model_dump_json()
        assert isinstance(json_str, str)
        assert "Paris Apartment" in json_str


class TestFlightDomainModels:
    """Test suite for flight-related domain models."""

    def test_airport_creation_success(self):
        """Test successful creation of airport."""
        airport = Airport(
            iata_code="JFK",
            name="John F. Kennedy International Airport",
            city="New York",
            country="United States",
            latitude=40.6413,
            longitude=-73.7781,
            timezone="America/New_York",
        )

        assert airport.iata_code == "JFK"
        assert airport.name == "John F. Kennedy International Airport"
        assert airport.city == "New York"
        assert airport.country == "United States"

    def test_airport_code_validation(self):
        """Test airport code validation."""
        # Test valid 3-character code - lowercase should be converted to uppercase
        airport = Airport(
            iata_code="jfk",
            name="JFK Airport",
            city="New York",
            country="United States",
        )
        assert airport.iata_code == "JFK"

        # Test invalid code length
        with pytest.raises(ValidationError, match="Airport code must be 3 characters"):
            Airport(
                iata_code="INVALID",  # Too long
                name="Test Airport",
                city="Test City",
                country="Test Country",
            )

    def test_flight_segment_creation_success(self):
        """Test successful creation of flight segment."""
        segment = FlightSegment(
            origin="JFK",
            destination="LAX",
            departure_date="2024-06-15",
            departure_time="10:30",
            arrival_date="2024-06-15",
            arrival_time="14:30",
            carrier="AA",
            flight_number="AA123",
            duration_minutes=360,
        )

        assert segment.origin == "JFK"
        assert segment.destination == "LAX"
        assert segment.departure_date == "2024-06-15"
        assert segment.flight_number == "AA123"
        assert segment.duration_minutes == 360

    def test_flight_segment_airport_code_validation(self):
        """Test flight segment airport code validation."""
        # Valid codes should be converted to uppercase
        segment = FlightSegment(
            origin="jfk",
            destination="lax",
            departure_date="2024-06-15",
        )
        assert segment.origin == "JFK"
        assert segment.destination == "LAX"

        # Invalid code length should raise error
        with pytest.raises(ValidationError):
            FlightSegment(
                origin="TOOLONG",
                destination="LAX",
                departure_date="2024-06-15",
            )

    def test_flight_offer_creation_success(self):
        """Test successful creation of flight offer."""
        offer = FlightOffer(
            id="flt-123",
            total_amount=450.00,
            total_currency="USD",
            base_amount=400.00,
            tax_amount=50.00,
            slices=[{"origin": "JFK", "destination": "LAX"}],
            passenger_count=1,
            cabin_class=CabinClass.ECONOMY,
            source="duffel",
        )

        assert offer.id == "flt-123"
        assert offer.total_amount == 450.00
        assert offer.total_currency == "USD"
        assert offer.passenger_count == 1
        assert offer.cabin_class == CabinClass.ECONOMY

    def test_cabin_class_enum(self):
        """Test CabinClass enum values."""
        assert CabinClass.ECONOMY == "economy"
        assert CabinClass.PREMIUM_ECONOMY == "premium_economy"
        assert CabinClass.BUSINESS == "business"
        assert CabinClass.FIRST == "first"


class TestMemoryDomainModels:
    """Test suite for memory-related domain models."""

    def test_entity_creation_success(self):
        """Test successful creation of entity."""
        entity = Entity(
            name="John Doe",
            entity_type="User",
            observations=["Prefers budget travel", "Likes cultural activities"],
            confidence_score=0.8,
            source="user_conversation",
            tags=["user", "preferences"],
        )

        assert entity.name == "John Doe"
        assert entity.entity_type == "User"
        assert len(entity.observations) == 2
        assert entity.confidence_score == 0.8
        assert "user" in entity.tags

    def test_entity_confidence_score_validation(self):
        """Test entity confidence score validation."""
        # Valid confidence score
        entity = Entity(
            name="Test Entity",
            entity_type="Test",
            confidence_score=0.5,
        )
        assert entity.confidence_score == 0.5

        # Invalid confidence score - too high
        with pytest.raises(ValidationError):
            Entity(
                name="Test Entity",
                entity_type="Test",
                confidence_score=1.5,  # > 1.0
            )

        # Invalid confidence score - negative
        with pytest.raises(ValidationError):
            Entity(
                name="Test Entity",
                entity_type="Test",
                confidence_score=-0.1,  # < 0.0
            )

    def test_relation_creation_success(self):
        """Test successful creation of relation."""
        relation = Relation(
            from_entity="John Doe",
            to_entity="Paris",
            relation_type="visited",
        )

        assert relation.from_entity == "John Doe"
        assert relation.to_entity == "Paris"
        assert relation.relation_type == "visited"


@pytest.mark.parametrize(
    "model_class,valid_data,required_fields",
    [
        (
            AccommodationLocation,
            {"city": "Paris", "country": "France", "address": "123 Main St"},
            {"city", "country"},
        ),
        (AccommodationAmenity, {"name": "Free WiFi", "category": "Internet"}, {"name"}),
        (
            Airport,
            {"iata_code": "JFK", "name": "JFK Airport", "city": "NYC", "country": "US"},
            {"iata_code", "name", "city", "country"},
        ),
        (
            FlightSegment,
            {"origin": "JFK", "destination": "LAX", "departure_date": "2024-06-15"},
            {"origin", "destination", "departure_date"},
        ),
        (
            Entity,
            {"name": "Test Entity", "entity_type": "Test"},
            {"name", "entity_type"},
        ),
        (
            Relation,
            {"from_entity": "Entity1", "to_entity": "Entity2", "relation_type": "test"},
            {"from_entity", "to_entity", "relation_type"},
        ),
    ],
)
def test_model_creation_and_validation(model_class, valid_data, required_fields):
    """Test model creation with valid data and required field validation."""
    # Test successful creation with valid data
    instance = model_class(**valid_data)
    assert instance is not None

    # Test each required field individually
    for field in required_fields:
        incomplete_data = {k: v for k, v in valid_data.items() if k != field}
        with pytest.raises(ValidationError):
            model_class(**incomplete_data)


def test_accommodation_type_enum():
    """Test AccommodationType enum values."""
    assert AccommodationType.HOTEL == "hotel"
    assert AccommodationType.APARTMENT == "apartment"
    assert AccommodationType.HOSTEL == "hostel"
    assert AccommodationType.RESORT == "resort"


def test_model_serialization_patterns():
    """Test common serialization patterns across domain models."""
    # Test accommodation location
    location = AccommodationLocation(
        city="Paris",
        country="France",
        latitude=48.8566,
        longitude=2.3522,
    )

    # Test model_dump
    data = location.model_dump()
    assert isinstance(data, dict)
    assert data["city"] == "Paris"
    assert data["latitude"] == 48.8566

    # Test model_dump with exclude
    data_excluded = location.model_dump(exclude={"latitude", "longitude"})
    assert "latitude" not in data_excluded
    assert "longitude" not in data_excluded
    assert "city" in data_excluded

    # Test round-trip serialization
    recreated = AccommodationLocation.model_validate(data)
    assert recreated.city == location.city
    assert recreated.latitude == location.latitude

    # Test airport
    airport = Airport(iata_code="JFK", name="JFK Airport", city="NYC", country="US")
    airport_data = airport.model_dump()
    recreated_airport = Airport.model_validate(airport_data)
    assert recreated_airport.iata_code == airport.iata_code


def test_model_field_validation_error_messages():
    """Test that field validators provide clear error messages."""
    # Test airport code validation
    with pytest.raises(ValidationError) as exc_info:
        Airport(
            iata_code="INVALID",
            name="Test Airport",
            city="Test City",
            country="Test Country",
        )

    errors = exc_info.value.errors()
    assert any("Airport code must be 3 characters" in str(error) for error in errors)

    # Test entity confidence score validation
    with pytest.raises(ValidationError) as exc_info:
        Entity(
            name="Test Entity",
            entity_type="Test",
            confidence_score=1.5,
        )

    errors = exc_info.value.errors()
    assert any("less than or equal to 1" in str(error) for error in errors)


def test_model_default_values():
    """Test default values in domain models."""
    # Test entity with defaults
    entity = Entity(name="Test", entity_type="Test")
    assert entity.observations == []
    assert entity.aliases == []
    assert entity.tags == []
    assert entity.metadata == {}

    # Test accommodation image with defaults
    image = AccommodationImage(url="https://example.com/image.jpg")
    assert image.is_primary is False

    # Test accommodation listing with defaults
    location = AccommodationLocation(city="Test", country="Test")
    listing = AccommodationListing(
        id="test",
        name="Test Listing",
        property_type=AccommodationType.HOTEL,
        location=location,
        price_per_night=100.0,
        currency="USD",
        max_guests=2,
    )
    assert listing.amenities == []
    assert listing.images == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
