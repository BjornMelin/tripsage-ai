"""
Comprehensive tests for TripSage Core domain models using modern Pydantic v2 patterns.

This test module follows latest best practices from 2024:
- Tests actual domain models that exist in the codebase
- Pydantic v2 field validators and model validators
- Proper use of Field with constraints and validation
- Modern pytest fixtures and parameterization
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
    SessionMemory,
    TravelMemory,
)
from tripsage_core.models.domain.transportation import (
    TransportationLocation,
    TransportationOffer,
    TransportationProvider,
    TransportationVehicle,
)
from tripsage_core.models.domain.trip import (
    TripBudget,
    TripItinerary,
    TripLocation,
    TripPreferences,
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

    def test_accommodation_listing_with_amenities(self):
        """Test accommodation listing with amenities and images."""
        location = AccommodationLocation(city="Paris", country="France")
        amenity = AccommodationAmenity(name="Free WiFi")
        image = AccommodationImage(url="https://example.com/image.jpg")

        listing = AccommodationListing(
            id="acc-456",
            name="Paris Apartment",
            property_type=AccommodationType.APARTMENT,
            location=location,
            price_per_night=150.0,
            currency="EUR",
            max_guests=2,
            amenities=[amenity],
            images=[image],
        )

        assert len(listing.amenities) == 1
        assert listing.amenities[0].name == "Free WiFi"
        assert len(listing.images) == 1
        assert listing.images[0].url == "https://example.com/image.jpg"


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
        # Test valid 3-character code
        airport = Airport(
            iata_code="jfk",  # lowercase should be converted to uppercase
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

    def test_flight_offer_with_segments(self):
        """Test flight offer with parsed segments."""
        segment = FlightSegment(
            origin="JFK",
            destination="LAX",
            departure_date="2024-06-15",
        )

        offer = FlightOffer(
            id="flt-456",
            total_amount=600.00,
            total_currency="USD",
            slices=[],
            passenger_count=1,
            segments=[segment],
        )

        assert len(offer.segments) == 1
        assert offer.segments[0].origin == "JFK"
        assert offer.segments[0].destination == "LAX"


class TestMemoryDomainModels:
    """Test suite for memory-related domain models."""

    def test_entity_creation_success(self):
        """Test successful creation of entity."""
        entity = Entity(
            id="entity-123",
            label="User",
            properties={"name": "John Doe", "email": "john@example.com"},
        )

        assert entity.id == "entity-123"
        assert entity.label == "User"
        assert entity.properties["name"] == "John Doe"

    def test_relation_creation_success(self):
        """Test successful creation of relation."""
        relation = Relation(
            id="rel-123",
            source_id="entity-1",
            target_id="entity-2",
            relation_type="VISITED",
            properties={"date": "2024-06-15"},
        )

        assert relation.id == "rel-123"
        assert relation.source_id == "entity-1"
        assert relation.target_id == "entity-2"
        assert relation.relation_type == "VISITED"

    def test_travel_memory_creation_success(self):
        """Test successful creation of travel memory."""
        memory = TravelMemory(
            id="mem-123",
            user_id="user-456",
            content="User prefers budget accommodations",
            memory_type="preference",
            confidence_score=0.8,
        )

        assert memory.id == "mem-123"
        assert memory.user_id == "user-456"
        assert memory.content == "User prefers budget accommodations"
        assert memory.memory_type == "preference"
        assert memory.confidence_score == 0.8

    def test_session_memory_creation_success(self):
        """Test successful creation of session memory."""
        session_memory = SessionMemory(
            id="session-123",
            session_id="sess-456",
            user_id="user-789",
            context={"query": "Plan a trip to Paris"},
            extracted_entities=[],
            extracted_relations=[],
        )

        assert session_memory.id == "session-123"
        assert session_memory.session_id == "sess-456"
        assert session_memory.user_id == "user-789"
        assert session_memory.context["query"] == "Plan a trip to Paris"


class TestTransportationDomainModels:
    """Test suite for transportation-related domain models."""

    def test_transportation_location_creation_success(self):
        """Test successful creation of transportation location."""
        location = TransportationLocation(
            name="Union Station",
            address="123 Transit St",
            city="Washington",
            country="United States",
            latitude=38.8977,
            longitude=-77.0365,
        )

        assert location.name == "Union Station"
        assert location.address == "123 Transit St"
        assert location.city == "Washington"
        assert location.latitude == 38.8977

    def test_transportation_vehicle_creation_success(self):
        """Test successful creation of transportation vehicle."""
        vehicle = TransportationVehicle(
            id="vehicle-123",
            type="car",
            make="Toyota",
            model="Camry",
            year=2023,
            capacity=5,
            fuel_type="gasoline",
        )

        assert vehicle.id == "vehicle-123"
        assert vehicle.type == "car"
        assert vehicle.make == "Toyota"
        assert vehicle.model == "Camry"
        assert vehicle.year == 2023
        assert vehicle.capacity == 5

    def test_transportation_provider_creation_success(self):
        """Test successful creation of transportation provider."""
        provider = TransportationProvider(
            id="provider-123",
            name="Enterprise Rent-A-Car",
            type="car_rental",
            contact_info={"phone": "+1-855-266-9289"},
            rating=4.2,
        )

        assert provider.id == "provider-123"
        assert provider.name == "Enterprise Rent-A-Car"
        assert provider.type == "car_rental"
        assert provider.rating == 4.2

    def test_transportation_offer_creation_success(self):
        """Test successful creation of transportation offer."""
        location = TransportationLocation(
            name="Airport Terminal",
            city="New York",
            country="United States",
        )

        vehicle = TransportationVehicle(
            id="vehicle-456",
            type="car",
            make="Honda",
            model="Accord",
            year=2023,
            capacity=5,
        )

        offer = TransportationOffer(
            id="trans-123",
            pickup_location=location,
            dropoff_location=location,
            vehicle=vehicle,
            price=89.99,
            currency="USD",
            pickup_time="2024-06-15T10:00:00Z",
            dropoff_time="2024-06-16T10:00:00Z",
        )

        assert offer.id == "trans-123"
        assert offer.price == 89.99
        assert offer.currency == "USD"
        assert offer.vehicle.make == "Honda"


class TestTripDomainModels:
    """Test suite for trip-related domain models."""

    def test_trip_location_creation_success(self):
        """Test successful creation of trip location."""
        location = TripLocation(
            id="loc-123",
            name="Paris, France",
            country="France",
            city="Paris",
            latitude=48.8566,
            longitude=2.3522,
        )

        assert location.id == "loc-123"
        assert location.name == "Paris, France"
        assert location.country == "France"
        assert location.city == "Paris"

    def test_trip_budget_creation_success(self):
        """Test successful creation of trip budget."""
        budget = TripBudget(
            id="budget-123",
            total_amount=3000.00,
            currency="USD",
            accommodation_budget=1200.00,
            transportation_budget=800.00,
            food_budget=500.00,
            activity_budget=500.00,
        )

        assert budget.id == "budget-123"
        assert budget.total_amount == 3000.00
        assert budget.currency == "USD"
        assert budget.accommodation_budget == 1200.00

    def test_trip_preferences_creation_success(self):
        """Test successful creation of trip preferences."""
        preferences = TripPreferences(
            id="pref-123",
            travel_style="cultural",
            budget_level="mid_range",
            accommodation_types=["hotel", "apartment"],
            transportation_modes=["public_transit", "walking"],
            activity_interests=["museums", "local_food"],
        )

        assert preferences.id == "pref-123"
        assert preferences.travel_style == "cultural"
        assert preferences.budget_level == "mid_range"
        assert "hotel" in preferences.accommodation_types
        assert "museums" in preferences.activity_interests

    def test_trip_itinerary_creation_success(self):
        """Test successful creation of trip itinerary."""
        location = TripLocation(
            id="loc-456",
            name="Tokyo, Japan",
            country="Japan",
            city="Tokyo",
        )

        budget = TripBudget(
            id="budget-456",
            total_amount=2500.00,
            currency="USD",
        )

        preferences = TripPreferences(
            id="pref-456",
            travel_style="adventure",
            budget_level="mid_range",
        )

        itinerary = TripItinerary(
            id="trip-123",
            name="Tokyo Adventure",
            description="An exciting trip to Tokyo",
            destinations=[location],
            budget=budget,
            preferences=preferences,
            start_date="2024-07-01",
            end_date="2024-07-10",
            duration_days=10,
            status="planning",
        )

        assert itinerary.id == "trip-123"
        assert itinerary.name == "Tokyo Adventure"
        assert len(itinerary.destinations) == 1
        assert itinerary.destinations[0].city == "Tokyo"
        assert itinerary.duration_days == 10
        assert itinerary.status == "planning"


@pytest.mark.parametrize(
    "model_class,required_fields",
    [
        (AccommodationLocation, {"city", "country"}),
        (AccommodationAmenity, {"name"}),
        (Airport, {"iata_code", "name", "city", "country"}),
        (FlightSegment, {"origin", "destination", "departure_date"}),
        (Entity, {"id", "label"}),
        (TransportationLocation, {"name", "city", "country"}),
        (TripLocation, {"id", "name", "country", "city"}),
    ],
)
def test_required_fields_validation(model_class, required_fields):
    """Test that required fields are properly validated."""
    # Test with missing required fields
    with pytest.raises(ValidationError):
        model_class()

    # Test with all required fields provided
    minimal_data = {}
    for field in required_fields:
        if field in ["id", "name", "city", "country", "label"]:
            minimal_data[field] = f"test_{field}"
        elif field == "iata_code":
            minimal_data[field] = "JFK"
        elif field in ["origin", "destination"]:
            minimal_data[field] = "JFK"
        elif field == "departure_date":
            minimal_data[field] = "2024-06-15"

    # This should not raise an error
    instance = model_class(**minimal_data)
    assert instance is not None


def test_model_serialization_and_deserialization():
    """Test that models can be serialized and deserialized correctly."""
    # Test with accommodation location
    location = AccommodationLocation(
        city="Paris",
        country="France",
        address="123 Main St",
        latitude=48.8566,
        longitude=2.3522,
    )

    # Test model_dump
    data_dict = location.model_dump()
    assert isinstance(data_dict, dict)
    assert data_dict["city"] == "Paris"
    assert data_dict["latitude"] == 48.8566

    # Test model_dump_json
    json_str = location.model_dump_json()
    assert isinstance(json_str, str)
    assert "Paris" in json_str

    # Test round-trip
    recreated = AccommodationLocation.model_validate(data_dict)
    assert recreated.city == location.city
    assert recreated.latitude == location.latitude


def test_enum_validation():
    """Test enum validation in domain models."""
    # Test CabinClass enum
    assert CabinClass.ECONOMY == "economy"
    assert CabinClass.BUSINESS == "business"

    # Test AccommodationType enum
    assert AccommodationType.HOTEL == "hotel"
    assert AccommodationType.APARTMENT == "apartment"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
