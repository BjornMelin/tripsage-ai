"""
Transportation domain models tests for TripSage Core using modern Pydantic v2 patterns.

This test module focuses on transportation-related domain models:
- TransportationOffer, TransportationProvider, TransportationVehicle,
  TransportationLocation
- Field validators and constraints testing
- Serialization and validation patterns
"""

import pytest
from pydantic import ValidationError

from tripsage_core.models.domain.transportation import (
    TransportationLocation,
    TransportationOffer,
    TransportationProvider,
    TransportationVehicle,
)
from tripsage_core.models.schemas_common.enums import TransportationType


class TestTransportationDomainModels:
    """Test suite for transportation-related domain models."""

    def test_transportation_location_creation_success(self):
        """Test successful creation of transportation location."""
        location = TransportationLocation(
            name="Union Station",
            address="50 Massachusetts Ave NE",
            city="Washington",
            state="DC",
            country="United States",
            postal_code="20002",
            latitude=38.8977,
            longitude=-77.0365,
        )

        assert location.name == "Union Station"
        assert location.address == "50 Massachusetts Ave NE"
        assert location.city == "Washington"
        assert location.state == "DC"
        assert location.country == "United States"
        assert location.latitude == 38.8977
        assert location.longitude == -77.0365

    def test_transportation_location_required_fields(self):
        """Test transportation location required fields validation."""
        # Should work with just required fields
        location = TransportationLocation(
            city="Boston",
            country="United States",
        )
        assert location.city == "Boston"
        assert location.country == "United States"

        # Should fail without required fields
        with pytest.raises(ValidationError):
            TransportationLocation()

    def test_transportation_provider_creation_success(self):
        """Test successful creation of transportation provider."""
        provider = TransportationProvider(
            name="Enterprise Rent-A-Car",
            code="ENT",
            contact_info="+1-855-266-9289",
            rating=4.2,
        )

        assert provider.name == "Enterprise Rent-A-Car"
        assert provider.code == "ENT"
        assert provider.contact_info == "+1-855-266-9289"
        assert provider.rating == 4.2

    def test_transportation_vehicle_creation_success(self):
        """Test successful creation of transportation vehicle."""
        vehicle = TransportationVehicle(
            type="sedan",
            make="Toyota",
            model="Camry",
            license_plate="ABC123",
            capacity=5,
            amenities=["GPS", "Bluetooth", "Air Conditioning"],
        )

        assert vehicle.type == "sedan"
        assert vehicle.make == "Toyota"
        assert vehicle.model == "Camry"
        assert vehicle.license_plate == "ABC123"
        assert vehicle.capacity == 5
        assert len(vehicle.amenities) == 3
        assert "GPS" in vehicle.amenities

    def test_transportation_vehicle_capacity_validation(self):
        """Test vehicle capacity validation."""
        # Valid capacity
        vehicle = TransportationVehicle(
            type="sedan",
            capacity=4,
        )
        assert vehicle.capacity == 4

        # Invalid capacity - zero
        with pytest.raises(ValidationError, match="Capacity must be positive"):
            TransportationVehicle(
                type="sedan",
                capacity=0,
            )

        # Invalid capacity - negative
        with pytest.raises(ValidationError, match="Capacity must be positive"):
            TransportationVehicle(
                type="sedan",
                capacity=-1,
            )

    def test_transportation_offer_creation_success(self):
        """Test successful creation of transportation offer."""
        pickup_location = TransportationLocation(
            name="JFK Airport Terminal 1",
            city="New York",
            country="United States",
        )

        dropoff_location = TransportationLocation(
            name="Times Square",
            city="New York",
            country="United States",
        )

        provider = TransportationProvider(
            name="Yellow Cab",
            code="YC",
        )

        vehicle = TransportationVehicle(
            type="taxi",
            capacity=4,
        )

        offer = TransportationOffer(
            id="trans-123",
            transportation_type=TransportationType.TAXI,
            provider=provider,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_datetime="2024-06-15T10:00:00Z",
            dropoff_datetime="2024-06-15T11:30:00Z",
            price=75.50,
            currency="USD",
            vehicle=vehicle,
            distance_km=25.5,
            duration_minutes=90,
            source="taxi_api",
        )

        assert offer.id == "trans-123"
        assert offer.transportation_type == TransportationType.TAXI
        assert offer.provider.name == "Yellow Cab"
        assert offer.pickup_location.name == "JFK Airport Terminal 1"
        assert offer.dropoff_location.name == "Times Square"
        assert offer.price == 75.50
        assert offer.currency == "USD"
        assert offer.distance_km == 25.5
        assert offer.duration_minutes == 90

    def test_transportation_offer_price_validation(self):
        """Test transportation offer price validation."""
        pickup_location = TransportationLocation(
            city="Test City",
            country="Test Country",
        )

        dropoff_location = TransportationLocation(
            city="Test City 2",
            country="Test Country",
        )

        # Valid price
        offer = TransportationOffer(
            id="trans-valid",
            transportation_type=TransportationType.BUS,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_datetime="2024-06-15T10:00:00Z",
            dropoff_datetime="2024-06-15T11:00:00Z",
            price=25.00,
            currency="USD",
        )
        assert offer.price == 25.00

        # Invalid price - negative
        with pytest.raises(ValidationError, match="Price must be non-negative"):
            TransportationOffer(
                id="trans-invalid",
                transportation_type=TransportationType.BUS,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_datetime="2024-06-15T10:00:00Z",
                dropoff_datetime="2024-06-15T11:00:00Z",
                price=-10.00,
                currency="USD",
            )

    def test_transportation_offer_distance_validation(self):
        """Test transportation offer distance validation."""
        pickup_location = TransportationLocation(
            city="Test City",
            country="Test Country",
        )

        dropoff_location = TransportationLocation(
            city="Test City 2",
            country="Test Country",
        )

        # Valid distance
        offer = TransportationOffer(
            id="trans-dist-valid",
            transportation_type=TransportationType.RIDESHARE,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_datetime="2024-06-15T10:00:00Z",
            dropoff_datetime="2024-06-15T11:00:00Z",
            price=15.00,
            currency="USD",
            distance_km=10.5,
        )
        assert offer.distance_km == 10.5

        # Invalid distance - negative
        with pytest.raises(ValidationError, match="Distance must be non-negative"):
            TransportationOffer(
                id="trans-dist-invalid",
                transportation_type=TransportationType.RIDESHARE,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_datetime="2024-06-15T10:00:00Z",
                dropoff_datetime="2024-06-15T11:00:00Z",
                price=15.00,
                currency="USD",
                distance_km=-5.0,
            )

    def test_transportation_offer_duration_validation(self):
        """Test transportation offer duration validation."""
        pickup_location = TransportationLocation(
            city="Test City",
            country="Test Country",
        )

        dropoff_location = TransportationLocation(
            city="Test City 2",
            country="Test Country",
        )

        # Valid duration
        offer = TransportationOffer(
            id="trans-dur-valid",
            transportation_type=TransportationType.TRAIN,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_datetime="2024-06-15T10:00:00Z",
            dropoff_datetime="2024-06-15T12:00:00Z",
            price=45.00,
            currency="USD",
            duration_minutes=120,
        )
        assert offer.duration_minutes == 120

        # Invalid duration - zero
        with pytest.raises(ValidationError, match="Duration must be positive"):
            TransportationOffer(
                id="trans-dur-invalid",
                transportation_type=TransportationType.TRAIN,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_datetime="2024-06-15T10:00:00Z",
                dropoff_datetime="2024-06-15T12:00:00Z",
                price=45.00,
                currency="USD",
                duration_minutes=0,
            )

    def test_transportation_offer_serialization(self):
        """Test transportation offer serialization."""
        pickup_location = TransportationLocation(
            city="Boston",
            country="United States",
        )

        dropoff_location = TransportationLocation(
            city="Cambridge",
            country="United States",
        )

        offer = TransportationOffer(
            id="trans-serial",
            transportation_type=TransportationType.RIDESHARE,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_datetime="2024-06-15T09:00:00Z",
            dropoff_datetime="2024-06-15T09:30:00Z",
            price=12.50,
            currency="USD",
        )

        # Test model_dump
        data = offer.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "trans-serial"
        assert data["pickup_location"]["city"] == "Boston"
        assert data["dropoff_location"]["city"] == "Cambridge"
        assert data["price"] == 12.50

        # Test model_dump_json
        json_str = offer.model_dump_json()
        assert isinstance(json_str, str)
        assert "trans-serial" in json_str
        assert "Boston" in json_str


@pytest.mark.parametrize(
    "model_class,valid_data,required_fields",
    [
        (
            TransportationLocation,
            {"name": "Test Station", "city": "Test City", "country": "Test Country"},
            {"city", "country"},
        ),
        (TransportationProvider, {"name": "Test Provider", "code": "TP"}, {"name"}),
        (
            TransportationVehicle,
            {"type": "sedan", "make": "Toyota", "capacity": 4},
            {"type"},
        ),
    ],
)
def test_transportation_model_validation(model_class, valid_data, required_fields):
    """Test transportation model creation and required field validation."""
    # Test successful creation with valid data
    instance = model_class(**valid_data)
    assert instance is not None

    # Test each required field individually
    for field in required_fields:
        incomplete_data = {k: v for k, v in valid_data.items() if k != field}
        with pytest.raises(ValidationError):
            model_class(**incomplete_data)


def test_transportation_type_enum():
    """Test TransportationType enum values."""
    assert TransportationType.TAXI == "taxi"
    assert TransportationType.RIDESHARE == "rideshare"
    assert TransportationType.BUS == "bus"
    assert TransportationType.TRAIN == "train"
    assert TransportationType.CAR_RENTAL == "car_rental"
    assert TransportationType.PUBLIC_TRANSIT == "public_transit"
    assert TransportationType.SHUTTLE == "shuttle"
    assert TransportationType.FERRY == "ferry"


def test_transportation_model_defaults():
    """Test default values in transportation models."""
    # Test vehicle with defaults
    vehicle = TransportationVehicle(type="sedan")
    assert vehicle.amenities == []

    # Test location with minimal required fields
    location = TransportationLocation(city="Test", country="Test")
    assert location.name is None
    assert location.address is None
    assert location.latitude is None
    assert location.longitude is None

    # Test provider with minimal fields
    provider = TransportationProvider(name="Test Provider")
    assert provider.code is None
    assert provider.contact_info is None
    assert provider.rating is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
