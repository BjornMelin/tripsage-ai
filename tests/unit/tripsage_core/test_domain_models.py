"""
Comprehensive tests for TripSage Core domain models.

This module tests the core business domain models that represent
essential entities in the TripSage travel planning system.
"""

from datetime import datetime

import pytest

from tripsage_core.models.domain.accommodation import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
    PropertyType,
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


class TestAccommodationDomainModels:
    """Tests for accommodation domain models."""

    def test_property_type_enum(self):
        """Test PropertyType enum values."""
        assert PropertyType.HOTEL == "hotel"
        assert PropertyType.APARTMENT == "apartment"
        assert PropertyType.VILLA == "villa"
        assert PropertyType.RESORT == "resort"

    def test_accommodation_amenity_creation(self):
        """Test AccommodationAmenity model creation."""
        amenity = AccommodationAmenity(
            name="Free WiFi",
            category="Internet",
            description="High-speed wireless internet",
        )

        assert amenity.name == "Free WiFi"
        assert amenity.category == "Internet"
        assert amenity.description == "High-speed wireless internet"

    def test_accommodation_amenity_minimal(self):
        """Test AccommodationAmenity with minimal data."""
        amenity = AccommodationAmenity(name="Pool")

        assert amenity.name == "Pool"
        assert amenity.category is None
        assert amenity.description is None

    def test_accommodation_image_creation(self):
        """Test AccommodationImage model creation."""
        image = AccommodationImage(
            url="https://example.com/image.jpg",
            caption="Beautiful view",
            is_primary=True,
        )

        assert image.url == "https://example.com/image.jpg"
        assert image.caption == "Beautiful view"
        assert image.is_primary is True

    def test_accommodation_image_minimal(self):
        """Test AccommodationImage with minimal data."""
        image = AccommodationImage(url="https://example.com/image.jpg")

        assert image.url == "https://example.com/image.jpg"
        assert image.caption is None
        assert image.is_primary is False

    def test_accommodation_location_creation(self):
        """Test AccommodationLocation model creation."""
        location = AccommodationLocation(
            address="123 Main St",
            city="San Francisco",
            state="CA",
            country="USA",
            postal_code="94102",
            latitude=37.7749,
            longitude=-122.4194,
            neighborhood="Downtown",
        )

        assert location.address == "123 Main St"
        assert location.city == "San Francisco"
        assert location.state == "CA"
        assert location.country == "USA"
        assert location.postal_code == "94102"
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.neighborhood == "Downtown"

    def test_accommodation_location_minimal(self):
        """Test AccommodationLocation with minimal required data."""
        location = AccommodationLocation(city="Paris", country="France")

        assert location.city == "Paris"
        assert location.country == "France"
        assert location.address is None
        assert location.state is None

    def test_accommodation_listing_creation(self):
        """Test AccommodationListing model creation."""
        location = AccommodationLocation(city="Paris", country="France")
        amenity = AccommodationAmenity(name="WiFi")
        image = AccommodationImage(url="https://example.com/image.jpg")

        listing = AccommodationListing(
            id="listing-123",
            name="Luxury Apartment",
            description="Beautiful apartment in central Paris",
            property_type=PropertyType.APARTMENT,
            location=location,
            price_per_night=150.0,
            currency="EUR",
            rating=4.8,
            review_count=125,
            amenities=[amenity],
            images=[image],
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1.5,
            check_in_time="15:00",
            check_out_time="11:00",
            source="airbnb",
        )

        assert listing.id == "listing-123"
        assert listing.name == "Luxury Apartment"
        assert listing.property_type == PropertyType.APARTMENT
        assert listing.location.city == "Paris"
        assert listing.price_per_night == 150.0
        assert listing.currency == "EUR"
        assert listing.rating == 4.8
        assert listing.review_count == 125
        assert len(listing.amenities) == 1
        assert listing.amenities[0].name == "WiFi"
        assert len(listing.images) == 1
        assert listing.max_guests == 4
        assert listing.source == "airbnb"

    def test_accommodation_listing_minimal(self):
        """Test AccommodationListing with minimal required data."""
        location = AccommodationLocation(city="Tokyo", country="Japan")

        listing = AccommodationListing(
            id="listing-456",
            name="Budget Room",
            property_type=PropertyType.HOTEL,
            location=location,
            price_per_night=50.0,
            currency="JPY",
            max_guests=2,
        )

        assert listing.id == "listing-456"
        assert listing.name == "Budget Room"
        assert listing.property_type == PropertyType.HOTEL
        assert listing.max_guests == 2
        assert listing.amenities == []
        assert listing.images == []


class TestFlightDomainModels:
    """Tests for flight domain models."""

    def test_cabin_class_enum(self):
        """Test CabinClass enum values."""
        assert CabinClass.ECONOMY == "economy"
        assert CabinClass.PREMIUM_ECONOMY == "premium_economy"
        assert CabinClass.BUSINESS == "business"
        assert CabinClass.FIRST == "first"

    def test_airport_creation(self):
        """Test Airport model creation."""
        airport = Airport(
            iata_code="LAX",
            name="Los Angeles International Airport",
            city="Los Angeles",
            country="USA",
            latitude=33.9425,
            longitude=-118.4081,
            timezone="America/Los_Angeles",
        )

        assert airport.iata_code == "LAX"
        assert airport.name == "Los Angeles International Airport"
        assert airport.city == "Los Angeles"
        assert airport.country == "USA"
        assert airport.latitude == 33.9425
        assert airport.longitude == -118.4081
        assert airport.timezone == "America/Los_Angeles"

    def test_airport_code_validation(self):
        """Test airport code validation."""
        # Valid 3-character code
        airport = Airport(
            iata_code="nyc",  # Should be converted to uppercase
            name="Test Airport",
            city="New York",
            country="USA",
        )
        assert airport.iata_code == "NYC"

        # Invalid code length
        with pytest.raises(ValueError, match="Airport code must be 3 characters"):
            Airport(
                iata_code="INVALID", name="Test Airport", city="Test", country="Test"
            )

    def test_flight_segment_creation(self):
        """Test FlightSegment model creation."""
        segment = FlightSegment(
            origin="LAX",
            destination="JFK",
            departure_date="2025-06-01",
            departure_time="08:00",
            arrival_date="2025-06-01",
            arrival_time="16:30",
            carrier="AA",
            flight_number="AA123",
            duration_minutes=330,
        )

        assert segment.origin == "LAX"
        assert segment.destination == "JFK"
        assert segment.departure_date == "2025-06-01"
        assert segment.departure_time == "08:00"
        assert segment.carrier == "AA"
        assert segment.flight_number == "AA123"
        assert segment.duration_minutes == 330

    def test_flight_segment_airport_code_validation(self):
        """Test FlightSegment airport code validation."""
        # Valid codes (converted to uppercase)
        segment = FlightSegment(
            origin="lax", destination="jfk", departure_date="2025-06-01"
        )
        assert segment.origin == "LAX"
        assert segment.destination == "JFK"

        # Invalid code length
        with pytest.raises(ValueError, match="Airport code must be 3 characters"):
            FlightSegment(
                origin="INVALID", destination="JFK", departure_date="2025-06-01"
            )

    def test_flight_offer_creation(self):
        """Test FlightOffer model creation."""
        segment = FlightSegment(
            origin="LAX", destination="JFK", departure_date="2025-06-01"
        )

        offer = FlightOffer(
            id="offer-123",
            total_amount=450.0,
            total_currency="USD",
            base_amount=350.0,
            tax_amount=100.0,
            slices=[{"origin": "LAX", "destination": "JFK"}],
            passenger_count=1,
            cabin_class=CabinClass.ECONOMY,
            segments=[segment],
            departure_datetime="2025-06-01T08:00:00Z",
            arrival_datetime="2025-06-01T16:30:00Z",
            total_duration_minutes=330,
            stops_count=0,
            airlines=["American Airlines"],
            source="duffel",
        )

        assert offer.id == "offer-123"
        assert offer.total_amount == 450.0
        assert offer.total_currency == "USD"
        assert offer.base_amount == 350.0
        assert offer.tax_amount == 100.0
        assert offer.passenger_count == 1
        assert offer.cabin_class == CabinClass.ECONOMY
        assert len(offer.segments) == 1
        assert offer.segments[0].origin == "LAX"
        assert offer.total_duration_minutes == 330
        assert offer.stops_count == 0
        assert offer.source == "duffel"

    def test_flight_offer_minimal(self):
        """Test FlightOffer with minimal required data."""
        offer = FlightOffer(
            id="offer-456",
            total_amount=200.0,
            total_currency="EUR",
            slices=[{"origin": "CDG", "destination": "LHR"}],
            passenger_count=2,
        )

        assert offer.id == "offer-456"
        assert offer.total_amount == 200.0
        assert offer.passenger_count == 2
        assert offer.cabin_class is None
        assert offer.segments is None


class TestMemoryDomainModels:
    """Tests for memory and knowledge graph domain models."""

    def test_entity_creation(self):
        """Test Entity model creation."""
        now = datetime.utcnow()

        entity = Entity(
            name="Paris",
            entity_type="destination",
            observations=["Beautiful city", "Great food"],
            created_at=now,
            updated_at=now,
            aliases=["City of Light", "Paris, France"],
            confidence_score=0.95,
            source="user_input",
            tags=["europe", "france", "city"],
            metadata={"population": "2.2 million", "currency": "EUR"},
        )

        assert entity.name == "Paris"
        assert entity.entity_type == "destination"
        assert entity.observations == ["Beautiful city", "Great food"]
        assert entity.created_at == now
        assert entity.updated_at == now
        assert entity.aliases == ["City of Light", "Paris, France"]
        assert entity.confidence_score == 0.95
        assert entity.source == "user_input"
        assert entity.tags == ["europe", "france", "city"]
        assert entity.metadata["population"] == "2.2 million"

    def test_entity_minimal(self):
        """Test Entity with minimal required data."""
        entity = Entity(name="London", entity_type="destination")

        assert entity.name == "London"
        assert entity.entity_type == "destination"
        assert entity.observations == []
        assert entity.aliases == []
        assert entity.tags == []
        assert entity.metadata == {}

    def test_relation_creation(self):
        """Test Relation model creation."""
        now = datetime.utcnow()

        relation = Relation(
            from_entity="User",
            to_entity="Paris",
            relation_type="wants_to_visit",
            created_at=now,
            confidence_score=0.9,
            weight=0.8,
            properties={"priority": "high", "timeframe": "summer_2025"},
            source="conversation",
            bidirectional=False,
        )

        assert relation.from_entity == "User"
        assert relation.to_entity == "Paris"
        assert relation.relation_type == "wants_to_visit"
        assert relation.created_at == now
        assert relation.confidence_score == 0.9
        assert relation.weight == 0.8
        assert relation.properties["priority"] == "high"
        assert relation.source == "conversation"
        assert relation.bidirectional is False

    def test_relation_minimal(self):
        """Test Relation with minimal required data."""
        relation = Relation(
            from_entity="User", to_entity="Tokyo", relation_type="interested_in"
        )

        assert relation.from_entity == "User"
        assert relation.to_entity == "Tokyo"
        assert relation.relation_type == "interested_in"
        assert relation.properties == {}
        assert relation.bidirectional is False

    def test_travel_memory_creation(self):
        """Test TravelMemory model creation."""
        now = datetime.utcnow()

        travel_memory = TravelMemory(
            user_id="user-123",
            memory_type="preference",
            content="Prefers budget-friendly accommodations with good WiFi",
            travel_context={
                "trip_type": "business",
                "budget_range": "100-200",
                "preferred_amenities": ["wifi", "breakfast"],
            },
            destinations=["Paris", "London", "Berlin"],
            travel_dates={"start": "2025-07-01", "end": "2025-07-15"},
            preferences={
                "accommodation_type": "hotel",
                "max_budget_per_night": 150,
                "required_amenities": ["wifi"],
            },
            importance_score=0.8,
            tags=["business_travel", "europe", "budget"],
            created_at=now,
        )

        assert travel_memory.user_id == "user-123"
        assert travel_memory.memory_type == "preference"
        assert "budget-friendly" in travel_memory.content
        assert travel_memory.travel_context["trip_type"] == "business"
        assert travel_memory.destinations == ["Paris", "London", "Berlin"]
        assert travel_memory.travel_dates["start"] == "2025-07-01"
        assert travel_memory.preferences["accommodation_type"] == "hotel"
        assert travel_memory.importance_score == 0.8
        assert "business_travel" in travel_memory.tags

    def test_travel_memory_minimal(self):
        """Test TravelMemory with minimal required data."""
        travel_memory = TravelMemory(
            user_id="user-456",
            memory_type="experience",
            content="Had a great time in Tokyo",
        )

        assert travel_memory.user_id == "user-456"
        assert travel_memory.memory_type == "experience"
        assert travel_memory.content == "Had a great time in Tokyo"
        assert travel_memory.travel_context == {}
        assert travel_memory.destinations == []
        assert travel_memory.preferences == {}
        assert travel_memory.tags == []

    def test_session_memory_creation(self):
        """Test SessionMemory model creation."""
        now = datetime.utcnow()

        session_memory = SessionMemory(
            user_id="user-123",
            session_id="session-456",
            memory_type="conversation",
            content={
                "last_query": "Find hotels in Paris",
                "preferences": {"budget": 200},
            },
            created_at=now,
            expires_at=now,
            conversation_context={
                "current_topic": "accommodation_search",
                "search_criteria": {"location": "Paris", "budget": 200},
            },
            agent_state={"last_action": "search_hotels", "step": 3},
            user_preferences={"currency": "EUR", "language": "en"},
            interaction_count=5,
            last_activity=now,
        )

        assert session_memory.user_id == "user-123"
        assert session_memory.session_id == "session-456"
        assert session_memory.memory_type == "conversation"
        assert session_memory.content["last_query"] == "Find hotels in Paris"
        assert (
            session_memory.conversation_context["current_topic"]
            == "accommodation_search"
        )
        assert session_memory.agent_state["last_action"] == "search_hotels"
        assert session_memory.user_preferences["currency"] == "EUR"
        assert session_memory.interaction_count == 5

    def test_session_memory_minimal(self):
        """Test SessionMemory with minimal required data."""
        session_memory = SessionMemory(
            session_id="session-789", memory_type="temp", content={"data": "test"}
        )

        assert session_memory.session_id == "session-789"
        assert session_memory.memory_type == "temp"
        assert session_memory.content["data"] == "test"
        assert session_memory.user_id is None
        assert session_memory.conversation_context == {}
        assert session_memory.agent_state == {}
        assert session_memory.interaction_count == 0


class TestDomainModelIntegration:
    """Integration tests for domain models working together."""

    def test_accommodation_listing_with_complex_data(self):
        """Test AccommodationListing with complex nested data."""
        # Create complex nested objects
        amenities = [
            AccommodationAmenity(name="WiFi", category="Internet"),
            AccommodationAmenity(name="Pool", category="Recreation"),
            AccommodationAmenity(name="Gym", category="Fitness"),
        ]

        images = [
            AccommodationImage(url="https://example.com/1.jpg", is_primary=True),
            AccommodationImage(url="https://example.com/2.jpg"),
            AccommodationImage(url="https://example.com/3.jpg"),
        ]

        location = AccommodationLocation(
            address="456 Ocean Drive",
            city="Miami",
            state="FL",
            country="USA",
            latitude=25.7617,
            longitude=-80.1918,
        )

        listing = AccommodationListing(
            id="complex-listing",
            name="Luxury Ocean View Resort",
            property_type=PropertyType.RESORT,
            location=location,
            price_per_night=350.0,
            currency="USD",
            amenities=amenities,
            images=images,
            max_guests=6,
        )

        # Verify complex object relationships
        assert len(listing.amenities) == 3
        assert listing.amenities[0].name == "WiFi"
        assert listing.amenities[0].category == "Internet"

        assert len(listing.images) == 3
        assert listing.images[0].is_primary is True
        assert listing.images[1].is_primary is False

        assert listing.location.city == "Miami"
        assert listing.location.latitude == 25.7617

    def test_flight_offer_with_segments(self):
        """Test FlightOffer with multiple flight segments."""
        segments = [
            FlightSegment(
                origin="LAX",
                destination="DEN",
                departure_date="2025-06-01",
                carrier="UA",
                flight_number="UA1234",
            ),
            FlightSegment(
                origin="DEN",
                destination="JFK",
                departure_date="2025-06-01",
                carrier="UA",
                flight_number="UA5678",
            ),
        ]

        offer = FlightOffer(
            id="multi-segment-offer",
            total_amount=650.0,
            total_currency="USD",
            slices=[{"segments": 2}],
            passenger_count=1,
            segments=segments,
            stops_count=1,
            airlines=["United Airlines"],
        )

        assert len(offer.segments) == 2
        assert offer.segments[0].origin == "LAX"
        assert offer.segments[0].destination == "DEN"
        assert offer.segments[1].origin == "DEN"
        assert offer.segments[1].destination == "JFK"
        assert offer.stops_count == 1

    def test_knowledge_graph_entity_relation_chain(self):
        """Test creating a chain of entities and relations."""
        # Create entities
        user_entity = Entity(name="User", entity_type="person")
        paris_entity = Entity(name="Paris", entity_type="destination")
        hotel_entity = Entity(name="Hotel Ritz", entity_type="accommodation")

        # Create relations
        wants_visit_relation = Relation(
            from_entity="User", to_entity="Paris", relation_type="wants_to_visit"
        )

        stays_at_relation = Relation(
            from_entity="User", to_entity="Hotel Ritz", relation_type="stays_at"
        )

        located_in_relation = Relation(
            from_entity="Hotel Ritz", to_entity="Paris", relation_type="located_in"
        )

        # Verify entity and relation structure
        assert user_entity.entity_type == "person"
        assert paris_entity.entity_type == "destination"
        assert hotel_entity.entity_type == "accommodation"

        assert wants_visit_relation.from_entity == "User"
        assert wants_visit_relation.to_entity == "Paris"
        assert stays_at_relation.relation_type == "stays_at"
        assert located_in_relation.from_entity == "Hotel Ritz"
        assert located_in_relation.to_entity == "Paris"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
