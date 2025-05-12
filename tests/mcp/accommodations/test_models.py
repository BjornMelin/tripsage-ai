"""
Tests for the Pydantic models in the accommodations module.

These tests verify that the models properly validate input data,
handle serialization correctly, and enforce validation constraints.
"""

import json
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.mcp.accommodations.models import (
    AccommodationSearchParams,
    AccommodationType,
    AirbnbHost,
    AirbnbListing,
    AirbnbListingDetails,
    AirbnbSearchParams,
    AirbnbSearchResult,
)


class TestAccommodationType:
    """Tests for the AccommodationType enum."""

    def test_enum_values(self):
        """Test that enum values are correct."""
        assert AccommodationType.ALL == "all"
        assert AccommodationType.APARTMENT == "apartment"
        assert AccommodationType.HOUSE == "house"
        assert AccommodationType.HOTEL == "hotel"
        assert AccommodationType.GUESTHOUSE == "guesthouse"
        assert AccommodationType.BED_AND_BREAKFAST == "bed_and_breakfast"
        assert AccommodationType.BOUTIQUE_HOTEL == "boutique_hotel"
        assert AccommodationType.VILLA == "villa"
        assert AccommodationType.CABIN == "cabin"
        assert AccommodationType.COTTAGE == "cottage"
        assert AccommodationType.OTHER == "other"


class TestAirbnbSearchParams:
    """Tests for the AirbnbSearchParams model."""

    def test_valid_minimal_params(self):
        """Test that minimal valid parameters work."""
        params = AirbnbSearchParams(location="San Francisco, CA")
        assert params.location == "San Francisco, CA"
        assert params.adults == 1
        assert params.checkin is None
        assert params.checkout is None
        assert params.min_price is None
        assert params.max_price is None

    def test_valid_full_params(self):
        """Test with all parameters provided."""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)

        params = AirbnbSearchParams(
            location="New York City, NY",
            place_id="ChIJOwg_06VPwokRYv534QaPC8g",
            checkin=tomorrow,
            checkout=next_week,
            adults=2,
            children=1,
            infants=1,
            pets=1,
            min_price=100,
            max_price=300,
            min_beds=2,
            min_bedrooms=1,
            min_bathrooms=1,
            property_type=AccommodationType.APARTMENT,
            amenities=["wifi", "kitchen"],
            room_type="entire_home",
            superhost=True,
            cursor="abc123",
            ignore_robots_txt=True,
        )

        assert params.location == "New York City, NY"
        assert params.place_id == "ChIJOwg_06VPwokRYv534QaPC8g"
        assert params.checkin == tomorrow.isoformat()
        assert params.checkout == next_week.isoformat()
        assert params.adults == 2
        assert params.children == 1
        assert params.infants == 1
        assert params.pets == 1
        assert params.min_price == 100
        assert params.max_price == 300
        assert params.min_beds == 2
        assert params.min_bedrooms == 1
        assert params.min_bathrooms == 1
        assert params.property_type == AccommodationType.APARTMENT
        assert params.amenities == ["wifi", "kitchen"]
        assert params.room_type == "entire_home"
        assert params.superhost is True
        assert params.cursor == "abc123"
        assert params.ignore_robots_txt is True

    def test_date_string_format(self):
        """Test that date strings are validated correctly."""
        # Valid format
        params = AirbnbSearchParams(
            location="Miami, FL",
            checkin="2024-06-01",
            checkout="2024-06-07",
        )
        assert params.checkin == "2024-06-01"
        assert params.checkout == "2024-06-07"

        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            AirbnbSearchParams(
                location="Miami, FL",
                checkin="06/01/2024",  # Wrong format
            )
        assert "Date must be in YYYY-MM-DD format" in str(exc_info.value)

    def test_date_conversion(self):
        """Test that date objects are converted to strings."""
        today = date.today()
        next_week = today + timedelta(days=7)

        params = AirbnbSearchParams(
            location="Chicago, IL",
            checkin=today,
            checkout=next_week,
        )

        assert params.checkin == today.isoformat()
        assert params.checkout == next_week.isoformat()

    def test_adults_validation(self):
        """Test adults count validation."""
        # Valid
        params = AirbnbSearchParams(location="Seattle, WA", adults=16)
        assert params.adults == 16

        # Too many
        with pytest.raises(ValidationError) as exc_info:
            AirbnbSearchParams(location="Seattle, WA", adults=17)
        assert "Input should be less than or equal to 16" in str(exc_info.value)

        # Too few
        with pytest.raises(ValidationError) as exc_info:
            AirbnbSearchParams(location="Seattle, WA", adults=0)
        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            AirbnbSearchParams(
                location="Portland, OR",
                invalid_field="some value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_model_dump(self):
        """Test model serialization."""
        params = AirbnbSearchParams(
            location="Austin, TX",
            adults=2,
            min_price=100,
            max_price=200,
        )

        dumped = params.model_dump()
        assert dumped["location"] == "Austin, TX"
        assert dumped["adults"] == 2
        assert dumped["min_price"] == 100
        assert dumped["max_price"] == 200

    def test_model_dump_with_exclude_none(self):
        """Test model serialization with exclude_none=True."""
        params = AirbnbSearchParams(
            location="Austin, TX",
            adults=2,
        )

        dumped = params.model_dump(exclude_none=True)
        assert "location" in dumped
        assert "adults" in dumped
        assert "min_price" not in dumped
        assert "max_price" not in dumped


class TestAirbnbListing:
    """Tests for the AirbnbListing model."""

    def test_valid_minimal_listing(self):
        """Test with minimal valid data."""
        listing = AirbnbListing(
            id="12345678",
            name="Cozy apartment",
            url="https://www.airbnb.com/rooms/12345678",
            price_string="$150 per night",
            price_total=1050,
            location_info="Downtown, San Francisco",
            property_type="Apartment",
        )

        assert listing.id == "12345678"
        assert listing.name == "Cozy apartment"
        assert listing.url == "https://www.airbnb.com/rooms/12345678"
        assert listing.price_string == "$150 per night"
        assert listing.price_total == 1050
        assert listing.location_info == "Downtown, San Francisco"
        assert listing.property_type == "Apartment"

    def test_full_listing(self):
        """Test with all fields provided."""
        listing = AirbnbListing(
            id="12345678",
            name="Cozy apartment in downtown",
            url="https://www.airbnb.com/rooms/12345678",
            image="https://example.com/image.jpg",
            superhost=True,
            price_string="$150 per night",
            price_total=1050,
            price_per_night=150,
            currency="USD",
            rating=4.8,
            reviews_count=120,
            location_info="Downtown, San Francisco",
            property_type="Apartment",
            beds=2,
            bedrooms=1,
            bathrooms=1,
            max_guests=4,
            amenities=["WiFi", "Kitchen"],
        )

        assert listing.id == "12345678"
        assert listing.name == "Cozy apartment in downtown"
        assert listing.rating == 4.8
        assert listing.beds == 2
        assert listing.bedrooms == 1
        assert listing.bathrooms == 1
        assert listing.amenities == ["WiFi", "Kitchen"]

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        listing = AirbnbListing(
            id="12345678",
            name="Cozy apartment",
            url="https://www.airbnb.com/rooms/12345678",
            price_string="$150 per night",
            price_total=1050,
            location_info="Downtown, San Francisco",
            property_type="Apartment",
            extra_field="This is allowed",
        )

        # Access using direct attribute access for dynamic field
        assert listing.extra_field == "This is allowed"

        # Should be included in serialized output
        dumped = listing.model_dump()
        assert dumped["extra_field"] == "This is allowed"


class TestAirbnbHost:
    """Tests for the AirbnbHost model."""

    def test_host_minimal(self):
        """Test with minimal valid data."""
        host = AirbnbHost(
            name="John Doe",
        )

        assert host.name == "John Doe"
        assert host.superhost is False
        assert host.image is None
        assert host.response_rate is None

    def test_host_full(self):
        """Test with all fields provided."""
        host = AirbnbHost(
            name="John Doe",
            image="https://example.com/host.jpg",
            superhost=True,
            response_rate=95.5,
            response_time="within an hour",
            joined_date="2015-06-01",
            languages=["English", "Spanish"],
        )

        assert host.name == "John Doe"
        assert host.image == "https://example.com/host.jpg"
        assert host.superhost is True
        assert host.response_rate == 95.5
        assert host.response_time == "within an hour"
        assert host.joined_date == "2015-06-01"
        assert host.languages == ["English", "Spanish"]

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        host = AirbnbHost(
            name="John Doe",
            custom_field="Custom value",
        )

        # Access using direct attribute access for dynamic field
        assert host.custom_field == "Custom value"

        # Should be included in serialized output
        dumped = host.model_dump()
        assert dumped["custom_field"] == "Custom value"


class TestAirbnbSearchResult:
    """Tests for the AirbnbSearchResult model."""

    def test_empty_result(self):
        """Test with empty result."""
        result = AirbnbSearchResult(
            location="San Francisco, CA",
        )

        assert result.location == "San Francisco, CA"
        assert result.count == 0
        assert result.listings == []
        assert result.next_cursor is None
        assert result.search_params == {}
        assert result.error is None

    def test_result_with_listings(self):
        """Test with listings."""
        listing1 = AirbnbListing(
            id="12345678",
            name="Cozy apartment",
            url="https://www.airbnb.com/rooms/12345678",
            price_string="$150 per night",
            price_total=1050,
            location_info="Downtown, San Francisco",
            property_type="Apartment",
        )

        listing2 = AirbnbListing(
            id="87654321",
            name="Luxury condo",
            url="https://www.airbnb.com/rooms/87654321",
            price_string="$250 per night",
            price_total=1750,
            location_info="Nob Hill, San Francisco",
            property_type="Condominium",
        )

        result = AirbnbSearchResult(
            location="San Francisco, CA",
            count=2,
            listings=[listing1, listing2],
            next_cursor="abc123",
            search_params={"location": "San Francisco, CA", "adults": 2},
        )

        assert result.location == "San Francisco, CA"
        assert result.count == 2
        assert len(result.listings) == 2
        assert result.listings[0].id == "12345678"
        assert result.listings[1].id == "87654321"
        assert result.next_cursor == "abc123"
        assert result.search_params == {"location": "San Francisco, CA", "adults": 2}

    def test_result_with_error(self):
        """Test with error."""
        result = AirbnbSearchResult(
            location="San Francisco, CA",
            error="Failed to search: API error",
        )

        assert result.location == "San Francisco, CA"
        assert result.count == 0
        assert result.listings == []
        assert result.error == "Failed to search: API error"

    def test_model_dump_json(self):
        """Test JSON serialization."""
        listing = AirbnbListing(
            id="12345678",
            name="Cozy apartment",
            url="https://www.airbnb.com/rooms/12345678",
            price_string="$150 per night",
            price_total=1050,
            location_info="Downtown, San Francisco",
            property_type="Apartment",
        )

        result = AirbnbSearchResult(
            location="San Francisco, CA",
            count=1,
            listings=[listing],
            search_params={"location": "San Francisco, CA"},
        )

        json_str = result.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["location"] == "San Francisco, CA"
        assert parsed["count"] == 1
        assert len(parsed["listings"]) == 1
        assert parsed["listings"][0]["id"] == "12345678"


class TestAirbnbListingDetails:
    """Tests for the AirbnbListingDetails model."""

    def test_minimal_listing_details(self):
        """Test with minimal valid data."""
        host = AirbnbHost(name="John Doe")

        details = AirbnbListingDetails(
            id="12345678",
            url="https://www.airbnb.com/rooms/12345678",
            name="Cozy apartment",
            description="Beautiful apartment in downtown.",
            host=host,
            property_type="Apartment",
            location="Downtown, San Francisco",
        )

        assert details.id == "12345678"
        assert details.url == "https://www.airbnb.com/rooms/12345678"
        assert details.name == "Cozy apartment"
        assert details.description == "Beautiful apartment in downtown."
        assert details.host.name == "John Doe"
        assert details.property_type == "Apartment"
        assert details.location == "Downtown, San Francisco"
        assert details.amenities == []
        assert details.images == []
        assert details.currency == "USD"

    def test_full_listing_details(self):
        """Test with all fields provided."""
        host = AirbnbHost(
            name="John Doe",
            image="https://example.com/host.jpg",
            superhost=True,
        )

        details = AirbnbListingDetails(
            id="12345678",
            url="https://www.airbnb.com/rooms/12345678",
            name="Cozy apartment in downtown",
            description="Beautiful apartment located in the heart of downtown.",
            host=host,
            property_type="Apartment",
            location="Downtown, San Francisco",
            coordinates={"lat": 37.7749, "lng": -122.4194},
            amenities=["WiFi", "Kitchen", "Washer", "Dryer", "Free parking"],
            bedrooms=1,
            beds=2,
            bathrooms=1,
            max_guests=4,
            rating=4.8,
            reviews_count=120,
            reviews_summary=[
                {"category": "Cleanliness", "rating": 4.9},
                {"category": "Communication", "rating": 5.0},
                {"category": "Check-in", "rating": 4.7},
            ],
            price_per_night=150,
            price_total=1050,
            currency="USD",
            images=[
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg",
                "https://example.com/image3.jpg",
            ],
            check_in_time="3 PM - 8 PM",
            check_out_time="11 AM",
            house_rules=["No smoking", "No pets", "No parties"],
            cancellation_policy="Flexible",
        )

        assert details.id == "12345678"
        assert details.name == "Cozy apartment in downtown"
        assert details.host.name == "John Doe"
        assert details.host.superhost is True
        assert details.coordinates == {"lat": 37.7749, "lng": -122.4194}
        assert len(details.amenities) == 5
        assert details.bedrooms == 1
        assert details.beds == 2
        assert details.bathrooms == 1
        assert details.max_guests == 4
        assert details.rating == 4.8
        assert len(details.reviews_summary) == 3
        assert details.reviews_summary[0]["category"] == "Cleanliness"
        assert details.price_per_night == 150
        assert details.price_total == 1050
        assert len(details.images) == 3
        assert details.check_in_time == "3 PM - 8 PM"
        assert details.check_out_time == "11 AM"
        assert len(details.house_rules) == 3
        assert details.cancellation_policy == "Flexible"

    def test_nested_serialization(self):
        """Test serialization of nested models."""
        host = AirbnbHost(
            name="John Doe",
            superhost=True,
        )

        details = AirbnbListingDetails(
            id="12345678",
            url="https://www.airbnb.com/rooms/12345678",
            name="Cozy apartment",
            description="Beautiful apartment in downtown.",
            host=host,
            property_type="Apartment",
            location="Downtown, San Francisco",
            amenities=["WiFi", "Kitchen"],
        )

        dumped = details.model_dump()

        assert dumped["id"] == "12345678"
        assert dumped["host"]["name"] == "John Doe"
        assert dumped["host"]["superhost"] is True
        assert dumped["amenities"] == ["WiFi", "Kitchen"]


class TestAccommodationSearchParams:
    """Tests for the AccommodationSearchParams model."""

    def test_valid_minimal_params(self):
        """Test with minimal valid parameters."""
        params = AccommodationSearchParams(
            location="San Francisco, CA",
        )

        assert params.location == "San Francisco, CA"
        assert params.source == "airbnb"
        assert params.adults == 1
        assert params.checkin is None
        assert params.checkout is None
        assert params.min_price is None
        assert params.max_price is None

    def test_all_params(self):
        """Test with all parameters."""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)

        params = AccommodationSearchParams(
            location="New York City, NY",
            source="booking",
            checkin=tomorrow,
            checkout=next_week,
            adults=2,
            children=1,
            min_price=100,
            max_price=300,
            property_type=AccommodationType.HOTEL,
            min_rating=4.5,
            amenities=["wifi", "breakfast"],
        )

        assert params.location == "New York City, NY"
        assert params.source == "booking"
        assert params.checkin == tomorrow.isoformat()
        assert params.checkout == next_week.isoformat()
        assert params.adults == 2
        assert params.children == 1
        assert params.min_price == 100
        assert params.max_price == 300
        assert params.property_type == AccommodationType.HOTEL
        assert params.min_rating == 4.5
        assert params.amenities == ["wifi", "breakfast"]

    def test_rating_validation(self):
        """Test rating validation."""
        # Valid
        params = AccommodationSearchParams(
            location="Boston, MA",
            min_rating=4.5,
        )
        assert params.min_rating == 4.5

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            AccommodationSearchParams(
                location="Boston, MA",
                min_rating=5.1,
            )
        assert "Input should be less than or equal to 5" in str(exc_info.value)

        # Too low
        with pytest.raises(ValidationError) as exc_info:
            AccommodationSearchParams(
                location="Boston, MA",
                min_rating=-0.1,
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            AccommodationSearchParams(
                location="Denver, CO",
                invalid_field="some value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_date_validation_reused(self):
        """Test that the date validator is reused correctly."""
        # Valid
        params = AccommodationSearchParams(
            location="Las Vegas, NV",
            checkin="2024-06-01",
            checkout="2024-06-07",
        )
        assert params.checkin == "2024-06-01"
        assert params.checkout == "2024-06-07"

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            AccommodationSearchParams(
                location="Las Vegas, NV",
                checkin="06/01/2024",  # Wrong format
            )
        assert "Date must be in YYYY-MM-DD format" in str(exc_info.value)
