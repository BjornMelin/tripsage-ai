"""
Comprehensive tests for centralized schemas.

Tests all centralized schema models and enums for validation,
business logic, and integration functionality.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))

from datetime import date, datetime, time  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from tripsage_core.models.schemas_common import (  # noqa: E402
    # Enums
    AccommodationType,
    # Geographic
    Address,
    Airport,
    # Temporal
    Availability,
    # Base models
    BaseResponse,
    BookingStatus,
    BoundingBox,
    # Financial
    Budget,
    BusinessHours,
    Coordinates,
    Currency,
    CurrencyCode,
    DateRange,
    Duration,
    ErrorResponse,
    ExchangeRate,
    PaginatedResponse,
    PaginationMeta,
    Place,
    Price,
    PriceRange,
    Route,
    SuccessResponse,
    TimeRange,
    TripStatus,
    UserRole,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


class TestEnums:
    """Test all centralized enums."""

    def test_booking_status_values(self):
        """Test BookingStatus enum values."""
        assert BookingStatus.VIEWED == "viewed"
        assert BookingStatus.SAVED == "saved"
        assert BookingStatus.BOOKED == "booked"
        assert BookingStatus.CANCELLED == "cancelled"

    def test_trip_status_values(self):
        """Test TripStatus enum values."""
        assert TripStatus.PLANNING == "planning"
        assert TripStatus.BOOKED == "booked"
        assert TripStatus.IN_PROGRESS == "in_progress"
        assert TripStatus.COMPLETED == "completed"
        assert TripStatus.CANCELLED == "cancelled"

    def test_accommodation_type_values(self):
        """Test AccommodationType enum values."""
        assert AccommodationType.HOTEL == "hotel"
        assert AccommodationType.APARTMENT == "apartment"
        assert AccommodationType.BED_AND_BREAKFAST == "bed_and_breakfast"
        assert AccommodationType.GUEST_HOUSE == "guest_house"
        assert AccommodationType.ALL == "all"

    def test_currency_code_values(self):
        """Test CurrencyCode enum values."""
        assert CurrencyCode.USD == "USD"
        assert CurrencyCode.EUR == "EUR"
        assert CurrencyCode.GBP == "GBP"

    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"


class TestBaseModels:
    """Test base response models."""

    def test_base_response_creation(self):
        """Test BaseResponse model creation."""
        response = BaseResponse(success=True, message="Test message")

        assert response.success is True
        assert response.message == "Test message"
        assert isinstance(response.timestamp, datetime)

    def test_success_response(self):
        """Test SuccessResponse model."""
        data = {"key": "value", "number": 42}
        response = SuccessResponse(data=data, message="Success")

        assert response.success is True
        assert response.data == data
        assert response.message == "Success"

    def test_error_response(self):
        """Test ErrorResponse model."""
        details = {"field": "email", "issue": "invalid format"}
        response = ErrorResponse(
            message="Validation failed", error_code="VALIDATION_ERROR", details=details
        )

        assert response.success is False
        assert response.message == "Validation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.details == details

    def test_pagination_meta(self):
        """Test PaginationMeta model."""
        meta = PaginationMeta(
            page=2,
            per_page=10,
            total_items=50,
            total_pages=5,
            has_next=True,
            has_prev=True,
        )

        assert meta.page == 2
        assert meta.per_page == 10
        assert meta.total_items == 50
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_validation_error_response(self):
        """Test ValidationErrorResponse model."""
        validation_errors = [
            ValidationErrorDetail(
                field="email", message="Invalid email format", value="invalid-email"
            ),
            ValidationErrorDetail(field="age", message="Must be positive", value=-5),
        ]

        response = ValidationErrorResponse(
            message="Validation failed", validation_errors=validation_errors
        )

        assert response.success is False
        assert response.error_code == "VALIDATION_ERROR"
        assert len(response.validation_errors) == 2
        assert response.validation_errors[0].field == "email"


class TestFinancialModels:
    """Test financial models."""

    def test_currency_creation(self):
        """Test Currency model creation."""
        currency = Currency(
            code=CurrencyCode.USD, symbol="$", name="US Dollar", decimal_places=2
        )

        assert currency.code == CurrencyCode.USD
        assert currency.symbol == "$"
        assert currency.name == "US Dollar"
        assert currency.decimal_places == 2

    def test_currency_validation(self):
        """Test Currency model validation."""
        with pytest.raises(ValidationError) as excinfo:
            Currency(code=CurrencyCode.USD, decimal_places=5)

        assert "Input should be less than or equal to 4" in str(excinfo.value)

    def test_price_creation(self):
        """Test Price model creation."""
        price = Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)

        assert price.amount == Decimal("99.99")
        assert price.currency == CurrencyCode.USD

    def test_price_validation(self):
        """Test Price model validation."""
        with pytest.raises(ValidationError) as excinfo:
            Price(amount=Decimal("-10"), currency=CurrencyCode.USD)

        assert "Input should be greater than or equal to 0" in str(excinfo.value)

    def test_price_formatting(self):
        """Test Price formatting methods."""
        price = Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)

        assert price.to_float() == 99.99
        assert price.format("$") == "$99.99"

    def test_price_conversion(self):
        """Test Price currency conversion."""
        price = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        converted = price.convert_to(CurrencyCode.EUR, Decimal("0.85"))

        assert converted.amount == Decimal("85")
        assert converted.currency == CurrencyCode.EUR

    def test_price_range(self):
        """Test PriceRange model."""
        min_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("150"), currency=CurrencyCode.USD)

        price_range = PriceRange(min_price=min_price, max_price=max_price)

        test_price = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        assert price_range.contains(test_price)

        avg_price = price_range.average()
        assert avg_price.amount == Decimal("100")

    def test_price_range_validation(self):
        """Test PriceRange validation."""
        min_price = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)

        with pytest.raises(ValidationError) as excinfo:
            PriceRange(min_price=min_price, max_price=max_price)

        assert "Max price must be greater than or equal to min price" in str(
            excinfo.value
        )

    def test_budget_creation(self):
        """Test Budget model creation."""
        total_budget = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        spent = Price(amount=Decimal("300"), currency=CurrencyCode.USD)

        budget = Budget(total_budget=total_budget, spent=spent)

        assert budget.utilization_percentage() == 30.0
        assert not budget.is_over_budget()

        remaining = budget.calculate_remaining()
        assert remaining.amount == Decimal("700")

    def test_exchange_rate(self):
        """Test ExchangeRate model."""
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=Decimal("0.85"),
        )

        converted = rate.convert(Decimal("100"))
        assert converted == Decimal("85")

        inverse = rate.inverse()
        assert inverse.from_currency == CurrencyCode.EUR
        assert inverse.to_currency == CurrencyCode.USD


class TestGeographicModels:
    """Test geographic models."""

    def test_coordinates_creation(self):
        """Test Coordinates model creation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)

        assert coords.latitude == 40.7128
        assert coords.longitude == -74.0060

    def test_coordinates_validation(self):
        """Test Coordinates validation."""
        with pytest.raises(ValidationError) as excinfo:
            Coordinates(latitude=91, longitude=0)

        assert "Latitude must be between -90.0 and 90.0" in str(excinfo.value)

        with pytest.raises(ValidationError) as excinfo:
            Coordinates(latitude=0, longitude=181)

        assert "Longitude must be between -180.0 and 180.0" in str(excinfo.value)

    def test_coordinates_distance(self):
        """Test distance calculation between coordinates."""
        nyc = Coordinates(latitude=40.7128, longitude=-74.0060)
        london = Coordinates(latitude=51.5074, longitude=-0.1278)

        distance = nyc.distance_to(london)
        # Approximate distance between NYC and London
        assert 5500 < distance < 5600  # kilometers

    def test_address_creation(self):
        """Test Address model creation."""
        address = Address(
            street="123 Main St",
            city="New York",
            state="NY",
            country="USA",
            postal_code="10001",
        )

        assert address.street == "123 Main St"
        assert address.city == "New York"
        assert "123 Main St" in address.to_string()
        assert "New York" in address.to_string()

    def test_place_creation(self):
        """Test Place model creation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        address = Address(city="New York", country="USA")

        place = Place(
            name="New York City",
            coordinates=coords,
            address=address,
            timezone="America/New_York",
        )

        assert place.name == "New York City"
        assert place.coordinates == coords
        assert place.address == address
        assert place.timezone == "America/New_York"

    def test_place_creation_with_invalid_timezone(self):
        """Test Place creation with invalid timezone (no validation implemented)."""
        # Note: Currently no timezone validation is implemented in Place model
        # This test documents the current behavior
        place = Place(name="Test", timezone="Invalid")
        assert place.name == "Test"
        assert place.timezone == "Invalid"  # No validation, accepts any string

    def test_bounding_box(self):
        """Test BoundingBox model."""
        bbox = BoundingBox(north=45, south=40, east=-70, west=-75)

        # Test coordinate within bounds
        coords_inside = Coordinates(latitude=42, longitude=-72)
        assert bbox.contains(coords_inside)

        # Test coordinate outside bounds
        coords_outside = Coordinates(latitude=50, longitude=-72)
        assert not bbox.contains(coords_outside)

        # Test center calculation
        center = bbox.center()
        assert center.latitude == 42.5  # (45 + 40) / 2
        assert center.longitude == -72.5  # (-70 + -75) / 2

    def test_airport_creation(self):
        """Test Airport model creation."""
        airport = Airport(
            code="JFK",
            icao_code="KJFK",
            name="John F. Kennedy International Airport",
            city="New York",
            country="USA",
        )

        assert airport.code == "JFK"
        assert airport.icao_code == "KJFK"
        assert airport.name == "John F. Kennedy International Airport"

    def test_airport_code_validation(self):
        """Test Airport code validation."""
        with pytest.raises(ValidationError) as excinfo:
            Airport(code="INVALID", name="Test", city="Test", country="Test")

        assert "Airport code must be exactly 3 characters (IATA code)" in str(
            excinfo.value
        )

    def test_route_creation(self):
        """Test Route model creation."""
        origin = Place(name="NYC")
        destination = Place(name="LAX")

        route = Route(
            origin=origin,
            destination=destination,
            distance_km=4000.0,
            duration_minutes=360,
        )

        assert route.origin.name == "NYC"
        assert route.destination.name == "LAX"
        assert route.distance_km == 4000.0


class TestTemporalModels:
    """Test temporal models."""

    def test_date_range_creation(self):
        """Test DateRange model creation."""
        start = date(2025, 6, 1)
        end = date(2025, 6, 15)

        date_range = DateRange(start_date=start, end_date=end)

        assert date_range.start_date == start
        assert date_range.end_date == end
        assert date_range.duration_days() == 14

    def test_date_range_validation(self):
        """Test DateRange validation."""
        start = date(2025, 6, 15)
        end = date(2025, 6, 1)  # End before start

        with pytest.raises(ValidationError) as excinfo:
            DateRange(start_date=start, end_date=end)

        assert "End date must be after start date" in str(excinfo.value)

    def test_date_range_contains(self):
        """Test DateRange contains method."""
        date_range = DateRange(start_date=date(2025, 6, 1), end_date=date(2025, 6, 15))

        assert date_range.contains(date(2025, 6, 10))
        assert not date_range.contains(date(2025, 5, 30))

    def test_time_range_creation(self):
        """Test TimeRange model creation."""
        start_time = time(9, 0)  # 9:00 AM
        end_time = time(17, 0)  # 5:00 PM

        time_range = TimeRange(start_time=start_time, end_time=end_time)

        assert time_range.start_time == start_time
        assert time_range.end_time == end_time
        assert time_range.duration_minutes() == 480  # 8 hours

    def test_duration_creation(self):
        """Test Duration model creation."""
        duration = Duration(days=1, hours=2, minutes=30)

        assert duration.total_minutes() == 24 * 60 + 2 * 60 + 30  # 1590 minutes
        assert duration.total_hours() == 26.5

    def test_duration_from_minutes(self):
        """Test Duration creation from total minutes."""
        duration = Duration.from_minutes(1590)  # 1 day, 2 hours, 30 minutes

        assert duration.days == 1
        assert duration.hours == 2
        assert duration.minutes == 30

    def test_duration_validation(self):
        """Test Duration validation."""
        with pytest.raises(ValidationError) as excinfo:
            Duration(hours=25)  # Invalid hours

        assert "Input should be less than 24" in str(excinfo.value)

    def test_availability_creation(self):
        """Test Availability model creation."""
        availability = Availability(
            available=True,
            from_datetime=datetime(2025, 6, 1, 9, 0),
            to_datetime=datetime(2025, 6, 1, 17, 0),
            capacity=50,
        )

        assert availability.available is True
        assert availability.capacity == 50

    def test_availability_validation(self):
        """Test Availability datetime validation."""
        with pytest.raises(ValidationError) as excinfo:
            Availability(
                available=True,
                from_datetime=datetime(2025, 6, 1, 17, 0),
                to_datetime=datetime(2025, 6, 1, 9, 0),  # End before start
            )

        assert "to_datetime must be after from_datetime" in str(excinfo.value)

    def test_business_hours(self):
        """Test BusinessHours model."""
        morning_hours = TimeRange(start_time=time(9, 0), end_time=time(17, 0))

        business_hours = BusinessHours(
            monday=morning_hours,
            tuesday=morning_hours,
            wednesday=morning_hours,
            thursday=morning_hours,
            friday=morning_hours,
            timezone="America/New_York",
        )

        # Test if open during business hours (Wednesday 2PM)
        check_time = datetime(2025, 6, 4, 14, 0)  # Wednesday 2PM
        assert business_hours.is_open_at(check_time)

        # Test if closed on weekend (Saturday 2PM)
        weekend_time = datetime(2025, 6, 7, 14, 0)  # Saturday 2PM
        assert not business_hours.is_open_at(weekend_time)


# Test data and fixtures
@pytest.fixture
def sample_coordinates():
    """Sample coordinates for testing."""
    return Coordinates(latitude=40.7128, longitude=-74.0060)


@pytest.fixture
def sample_price():
    """Sample price for testing."""
    return Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)


@pytest.fixture
def sample_address():
    """Sample address for testing."""
    return Address(
        street="123 Main St",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
    )


class TestIntegration:
    """Test integration between different schema models."""

    def test_place_with_coordinates_and_address(
        self, sample_coordinates, sample_address
    ):
        """Test Place model with both coordinates and address."""
        place = Place(
            name="Test Location",
            coordinates=sample_coordinates,
            address=sample_address,
            timezone="America/New_York",
        )

        assert place.coordinates.latitude == 40.7128
        assert place.address.city == "New York"
        assert "123 Main St" in place.address.to_string()

    def test_route_with_coordinates(self, sample_coordinates):
        """Test Route model with coordinate-based distance calculation."""
        origin = Place(name="Origin", coordinates=sample_coordinates)
        destination = Place(
            name="Destination",
            coordinates=Coordinates(latitude=34.0522, longitude=-118.2437),  # LA
        )

        route = Route(origin=origin, destination=destination)

        # Test calculated distance
        calculated_distance = route.total_distance()
        assert calculated_distance is not None
        assert calculated_distance > 3000  # NYC to LA is ~3900km

    def test_budget_with_multiple_currencies(self, sample_price):
        """Test Budget model with currency consistency validation."""
        eur_price = Price(amount=Decimal("50"), currency=CurrencyCode.EUR)

        with pytest.raises(ValidationError) as excinfo:
            Budget(total_budget=sample_price, spent=eur_price)

        assert "All budget amounts must use the same currency" in str(excinfo.value)

    def test_paginated_response_with_places(self, sample_coordinates, sample_address):
        """Test PaginatedResponse with Place objects."""
        places = [
            Place(name="Place 1", coordinates=sample_coordinates),
            Place(name="Place 2", address=sample_address),
        ]

        pagination = PaginationMeta(
            page=1,
            per_page=10,
            total_items=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )

        response = PaginatedResponse[Place](
            success=True, data=places, pagination=pagination
        )

        assert response.success is True
        assert len(response.data) == 2
        assert response.data[0].name == "Place 1"
        assert response.pagination.total_items == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_price(self):
        """Test zero price handling."""
        price = Price(amount=Decimal("0"), currency=CurrencyCode.USD)
        assert price.amount == Decimal("0")
        assert price.format() == "USD0.00"

    def test_coordinates_extreme_values(self):
        """Test coordinates at extreme valid values."""
        # North pole
        north_pole = Coordinates(latitude=90.0, longitude=0.0)
        assert north_pole.latitude == 90.0

        # South pole
        south_pole = Coordinates(latitude=-90.0, longitude=0.0)
        assert south_pole.latitude == -90.0

        # International date line
        dateline = Coordinates(latitude=0.0, longitude=180.0)
        assert dateline.longitude == 180.0

    def test_duration_edge_cases(self):
        """Test Duration with edge case values."""
        # Zero duration
        zero_duration = Duration(days=0, hours=0, minutes=0)
        assert zero_duration.total_minutes() == 0

        # Maximum valid time within a day
        max_duration = Duration(days=0, hours=23, minutes=59)
        assert max_duration.total_minutes() == 23 * 60 + 59

    def test_empty_address_formatting(self):
        """Test address formatting with minimal data."""
        empty_address = Address()
        assert empty_address.to_string() == ""

        city_only = Address(city="New York")
        assert city_only.to_string() == "New York"

    def test_bounding_box_edge_cases(self):
        """Test BoundingBox edge cases."""
        # Point bounding box (same coordinates)
        point_bbox = BoundingBox(north=40, south=40, east=-74, west=-74)
        point_coords = Coordinates(latitude=40, longitude=-74)
        assert point_bbox.contains(point_coords)

        center = point_bbox.center()
        assert center.latitude == 40
        assert center.longitude == -74
