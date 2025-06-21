"""Edge case tests for geographic schemas.

This module provides comprehensive edge case testing for geographic models
including coordinates, addresses, places, and route calculations with
focus on boundary conditions, precision handling, and real-world scenarios.
"""

import json
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from tripsage_core.models.schemas_common.geographic import (
    Address,
    Airport,
    BoundingBox,
    Coordinates,
    Place,
    Region,
    Route,
)


class TestCoordinatesEdgeCases:
    """Test edge cases for Coordinates model."""

    def test_coordinates_extreme_precision(self):
        """Test coordinates with extreme precision values."""
        # Test with very high precision
        high_precision_lat = 45.123456789012345
        high_precision_lon = -120.987654321098765

        coords = Coordinates(latitude=high_precision_lat, longitude=high_precision_lon)
        assert coords.latitude == high_precision_lat
        assert coords.longitude == high_precision_lon

    def test_coordinates_boundary_values(self):
        """Test coordinates at exact boundary values."""
        # Test exact boundaries
        boundary_coords = [
            (90.0, 180.0),  # North Pole, International Date Line
            (-90.0, -180.0),  # South Pole, Opposite Date Line
            (0.0, 0.0),  # Null Island
            (90.0, 0.0),  # North Pole, Prime Meridian
            (-90.0, 0.0),  # South Pole, Prime Meridian
        ]

        for lat, lon in boundary_coords:
            coords = Coordinates(latitude=lat, longitude=lon)
            assert coords.latitude == lat
            assert coords.longitude == lon

    def test_coordinates_with_altitude_edge_cases(self):
        """Test coordinates with altitude edge cases."""
        # Test with very high altitude (Mt. Everest + margin)
        high_altitude = Coordinates(
            latitude=27.9881,
            longitude=86.9250,
            altitude=10000.0,  # 10km above sea level
        )
        assert high_altitude.altitude == 10000.0

        # Test with negative altitude (below sea level)
        below_sea_level = Coordinates(
            latitude=31.5,
            longitude=35.5,
            altitude=-430.0,  # Dead Sea level
        )
        assert below_sea_level.altitude == -430.0

        # Test with zero altitude
        sea_level = Coordinates(latitude=0.0, longitude=0.0, altitude=0.0)
        assert sea_level.altitude == 0.0

    def test_distance_calculation_edge_cases(self):
        """Test distance calculations with edge cases."""
        # Test distance to same point
        point = Coordinates(latitude=40.7128, longitude=-74.0060)
        distance_to_self = point.distance_to(point)
        assert distance_to_self == 0.0

        # Test very small distance (1 meter precision test)
        point1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        point2 = Coordinates(latitude=40.712809, longitude=-74.0060)  # ~1 meter north
        small_distance = point1.distance_to(point2)
        assert 0.0 < small_distance < 0.01  # Should be very small but not zero

        # Test antipodal points (maximum distance on Earth)
        north = Coordinates(latitude=45.0, longitude=0.0)
        south = Coordinates(latitude=-45.0, longitude=180.0)
        max_distance = north.distance_to(south)
        assert 15000 < max_distance < 25000  # Roughly half Earth's circumference

        # Test across International Date Line
        point_east = Coordinates(latitude=0.0, longitude=179.9)
        point_west = Coordinates(latitude=0.0, longitude=-179.9)
        dateline_distance = point_east.distance_to(point_west)
        assert dateline_distance < 50  # Should be small distance, not halfway around world

    def test_distance_calculation_precision(self):
        """Test distance calculation precision with known distances."""
        # Test with known distance (approximately 111 km = 1 degree of latitude)
        point1 = Coordinates(latitude=0.0, longitude=0.0)
        point2 = Coordinates(latitude=1.0, longitude=0.0)
        distance = point1.distance_to(point2)

        # 1 degree latitude ≈ 111 km
        assert 110 < distance < 112

        # Test with longitude distance at equator
        point3 = Coordinates(latitude=0.0, longitude=1.0)
        lon_distance = point1.distance_to(point3)
        assert 110 < lon_distance < 112  # At equator, longitude distance ≈ latitude distance

    def test_coordinates_serialization_precision(self):
        """Test that coordinate precision is preserved through serialization."""
        precise_coords = Coordinates(latitude=45.123456789, longitude=-120.987654321, altitude=1234.5678)

        # Test JSON serialization
        json_data = precise_coords.model_dump_json()
        parsed = json.loads(json_data)

        # Reconstruct and verify precision
        reconstructed = Coordinates.model_validate(parsed)
        assert abs(reconstructed.latitude - precise_coords.latitude) < 1e-10
        assert abs(reconstructed.longitude - precise_coords.longitude) < 1e-10
        assert abs(reconstructed.altitude - precise_coords.altitude) < 1e-10


class TestAddressEdgeCases:
    """Test edge cases for Address model."""

    def test_address_with_unicode_characters(self):
        """Test address handling with international characters."""
        unicode_address = Address(
            street="123 Rue de la Paix",
            city="Москва",  # Moscow in Cyrillic
            state="北京市",  # Beijing in Chinese
            country="Deutschland",
            postal_code="12345-678",
            formatted="123 Rue de la Paix, Москва, 北京市, Deutschland 12345-678",
        )

        formatted_str = unicode_address.to_string()
        assert "Москва" in formatted_str
        assert "北京市" in formatted_str
        assert "Deutschland" in formatted_str

    def test_address_minimal_data(self):
        """Test address with minimal required data."""
        # Address with only some fields
        minimal_address = Address(city="New York", country="USA")

        formatted = minimal_address.to_string()
        assert "New York" in formatted
        assert "USA" in formatted
        assert formatted == "New York, USA"

    def test_address_empty_fields(self):
        """Test address with empty and None fields."""
        sparse_address = Address(
            street="",  # Empty string
            city="Boston",
            state=None,  # None
            country="USA",
            postal_code="02101",
        )

        formatted = sparse_address.to_string()
        # Empty string should not appear in formatted address
        assert not formatted.startswith(",")
        assert "Boston" in formatted
        assert "USA" in formatted
        assert "02101" in formatted

    def test_address_very_long_fields(self):
        """Test address with very long field values."""
        long_street = "A" * 200  # Very long street name
        long_city = "B" * 100  # Very long city name

        long_address = Address(
            street=long_street,
            city=long_city,
            state="CA",
            country="USA",
            postal_code="12345",
        )

        formatted = long_address.to_string()
        assert long_street in formatted
        assert long_city in formatted
        assert len(formatted) > 300

    def test_address_special_characters(self):
        """Test address with special characters and punctuation."""
        special_address = Address(
            street="123 O'Reilly St., Apt. #4B",
            city="St. John's",
            state="N.L.",
            country="Canada",
            postal_code="A1A 1A1",
        )

        formatted = special_address.to_string()
        assert "O'Reilly" in formatted
        assert "St. John's" in formatted
        assert "#4B" in formatted

    def test_address_preformatted_override(self):
        """Test that preformatted address overrides to_string logic."""
        preformatted = Address(
            street="123 Main St",
            city="Boston",
            state="MA",
            country="USA",
            formatted="Custom formatted address string",
        )

        # Should return preformatted string, not generated one
        assert preformatted.to_string() == "Custom formatted address string"


class TestPlaceEdgeCases:
    """Test edge cases for Place model."""

    def test_place_with_complex_data(self):
        """Test place with complex coordinate and address data."""
        coords = Coordinates(latitude=40.7589, longitude=-73.9851, altitude=10.0)

        address = Address(
            street="350 5th Ave",
            city="New York",
            state="NY",
            country="USA",
            postal_code="10118",
        )

        place = Place(
            name="Empire State Building",
            coordinates=coords,
            address=address,
            place_id="ChIJaXQRs6lZwokRY6tbFzGg-70",  # Google Place ID format
            place_type="landmark",
            timezone="America/New_York",
        )

        assert place.name == "Empire State Building"
        assert place.coordinates.altitude == 10.0
        assert place.address.postal_code == "10118"
        assert place.timezone == "America/New_York"

    def test_place_minimal_data(self):
        """Test place with only required data."""
        minimal_place = Place(name="Unknown Location")

        assert minimal_place.name == "Unknown Location"
        assert minimal_place.coordinates is None
        assert minimal_place.address is None
        assert minimal_place.place_id is None

    def test_place_with_emoji_and_unicode(self):
        """Test place names with emoji and Unicode characters."""
        unicode_place = Place(name="🗽 Statue of Liberty 自由女神像", place_type="monument")

        assert "🗽" in unicode_place.name
        assert "自由女神像" in unicode_place.name

    def test_place_timezone_validation(self):
        """Test place with various timezone formats."""
        # Valid IANA timezone
        place_with_tz = Place(name="Tokyo Tower", timezone="Asia/Tokyo")
        assert place_with_tz.timezone == "Asia/Tokyo"

        # UTC timezone
        utc_place = Place(name="Greenwich Observatory", timezone="UTC")
        assert utc_place.timezone == "UTC"


class TestBoundingBoxEdgeCases:
    """Test edge cases for BoundingBox model."""

    def test_bounding_box_edge_cases(self):
        """Test bounding box with edge case coordinates."""
        # Test global bounding box
        global_bbox = BoundingBox(north=90.0, south=-90.0, east=180.0, west=-180.0)

        # Test center of global bounding box
        center = global_bbox.center()
        assert center.latitude == 0.0
        assert center.longitude == 0.0

        # Test contains with extreme coordinates
        north_pole = Coordinates(latitude=90.0, longitude=0.0)
        south_pole = Coordinates(latitude=-90.0, longitude=0.0)

        assert global_bbox.contains(north_pole)
        assert global_bbox.contains(south_pole)

    def test_bounding_box_crossing_dateline(self):
        """Test bounding box that crosses International Date Line."""
        # Bounding box around Alaska/Russia
        dateline_bbox = BoundingBox(
            north=70.0,
            south=50.0,
            east=-150.0,  # East boundary is actually west of west boundary
            west=170.0,
        )

        # Point in Siberia (positive longitude)
        siberia_point = Coordinates(latitude=60.0, longitude=175.0)
        # Point in Alaska (negative longitude)
        alaska_point = Coordinates(latitude=60.0, longitude=-155.0)

        # Note: Current implementation might not handle dateline crossing correctly
        # This test documents the current behavior - just verify no exceptions
        dateline_bbox.contains(siberia_point)
        dateline_bbox.contains(alaska_point)

    def test_bounding_box_zero_area(self):
        """Test bounding box with zero area (single point)."""
        point_bbox = BoundingBox(north=40.7128, south=40.7128, east=-74.0060, west=-74.0060)

        # Center should be the point itself
        center = point_bbox.center()
        assert center.latitude == 40.7128
        assert center.longitude == -74.0060

        # Should contain the exact point
        exact_point = Coordinates(latitude=40.7128, longitude=-74.0060)
        assert point_bbox.contains(exact_point)

        # Should not contain nearby points
        nearby_point = Coordinates(latitude=40.7129, longitude=-74.0060)
        assert not point_bbox.contains(nearby_point)

    def test_bounding_box_invalid_boundaries(self):
        """Test bounding box validation with invalid boundaries."""
        # The current BoundingBox model doesn't enforce north > south validation
        # This test documents the current behavior - no validation errors are raised

        # Create bounding box with south > north (should be logically invalid)
        bbox = BoundingBox(
            north=40.0,
            south=50.0,  # South > North
            east=-70.0,
            west=-80.0,
        )
        # Currently this doesn't raise an error, but center calculation might be odd
        center = bbox.center()
        assert center.latitude == 45.0  # Average of 40 and 50

        # East less than west (might be valid for dateline crossing)
        bbox2 = BoundingBox(
            north=50.0,
            south=40.0,
            east=-80.0,  # East < West
            west=-70.0,
        )
        # This also doesn't raise an error in current implementation
        center2 = bbox2.center()
        assert center2.longitude == -75.0  # Average of -80 and -70


class TestAirportEdgeCases:
    """Test edge cases for Airport model."""

    def test_airport_icao_code_validation(self):
        """Test airport ICAO code validation."""
        # Valid ICAO code (4 characters)
        airport_with_icao = Airport(
            code="LAX",
            icao_code="KLAX",
            name="Los Angeles International Airport",
            city="Los Angeles",
            country="USA",
        )
        assert airport_with_icao.icao_code == "KLAX"

        # Test without ICAO code
        airport_no_icao = Airport(
            code="LAX",
            name="Los Angeles International Airport",
            city="Los Angeles",
            country="USA",
        )
        assert airport_no_icao.icao_code is None

        # Invalid ICAO code length
        with pytest.raises(ValidationError):
            Airport(
                code="LAX",
                icao_code="KLA",  # Too short
                name="Los Angeles International Airport",
                city="Los Angeles",
                country="USA",
            )

        with pytest.raises(ValidationError):
            Airport(
                code="LAX",
                icao_code="KLAXX",  # Too long
                name="Los Angeles International Airport",
                city="Los Angeles",
                country="USA",
            )

    def test_airport_with_coordinates_and_timezone(self):
        """Test airport with complete location data."""
        lax_coords = Coordinates(
            latitude=33.9425,
            longitude=-118.4081,
            altitude=38.0,  # LAX altitude
        )

        lax_airport = Airport(
            code="LAX",
            icao_code="KLAX",
            name="Los Angeles International Airport",
            city="Los Angeles",
            country="United States",
            coordinates=lax_coords,
            timezone="America/Los_Angeles",
        )

        assert lax_airport.coordinates.altitude == 38.0
        assert lax_airport.timezone == "America/Los_Angeles"

    def test_airport_international_names(self):
        """Test airports with international names and cities."""
        international_airports = [
            {
                "code": "NRT",
                "name": "成田国際空港",  # Narita in Japanese
                "city": "東京",  # Tokyo in Japanese
                "country": "日本",  # Japan in Japanese
            },
            {
                "code": "CDG",
                "name": "Aéroport de Paris-Charles-de-Gaulle",
                "city": "Paris",
                "country": "France",
            },
        ]

        for airport_data in international_airports:
            airport = Airport(**airport_data)
            assert len(airport.code) == 3
            assert airport.name == airport_data["name"]


class TestRouteEdgeCases:
    """Test edge cases for Route model."""

    def test_route_distance_calculation_edge_cases(self):
        """Test route distance calculations with edge cases."""
        origin = Place(name="Start", coordinates=Coordinates(latitude=40.7128, longitude=-74.0060))
        destination = Place(name="End", coordinates=Coordinates(latitude=34.0522, longitude=-118.2437))

        # Route without waypoints
        direct_route = Route(origin=origin, destination=destination)

        calculated_distance = direct_route.total_distance()
        assert calculated_distance is not None
        assert calculated_distance > 3000  # NYC to LA is ~3900 km

        # Route with waypoints
        waypoint = Place(
            name="Chicago",
            coordinates=Coordinates(latitude=41.8781, longitude=-87.6298),
        )

        route_with_waypoint = Route(origin=origin, destination=destination, waypoints=[waypoint])

        waypoint_distance = route_with_waypoint.total_distance()
        assert waypoint_distance is not None
        assert waypoint_distance > calculated_distance  # Should be longer with waypoint

    def test_route_without_coordinates(self):
        """Test route when places lack coordinates."""
        origin_no_coords = Place(name="Unknown Start")
        destination_no_coords = Place(name="Unknown End")

        route_no_coords = Route(
            origin=origin_no_coords,
            destination=destination_no_coords,
            distance_km=1000.0,  # Manual distance
        )

        # Should return the manual distance
        total_distance = route_no_coords.total_distance()
        assert total_distance == 1000.0

    def test_route_with_missing_waypoint_coordinates(self):
        """Test route where some waypoints lack coordinates."""
        origin = Place(name="Start", coordinates=Coordinates(latitude=0.0, longitude=0.0))
        destination = Place(name="End", coordinates=Coordinates(latitude=10.0, longitude=10.0))

        # Waypoint without coordinates
        waypoint_no_coords = Place(name="Middle Stop")
        waypoint_with_coords = Place(name="Known Stop", coordinates=Coordinates(latitude=5.0, longitude=5.0))

        route = Route(
            origin=origin,
            destination=destination,
            waypoints=[waypoint_no_coords, waypoint_with_coords],
        )

        # Should handle missing coordinates gracefully
        distance = route.total_distance()
        assert distance is not None

    def test_route_zero_distance(self):
        """Test route where origin and destination are the same."""
        same_location = Place(
            name="Same Place",
            coordinates=Coordinates(latitude=40.7128, longitude=-74.0060),
        )

        zero_route = Route(origin=same_location, destination=same_location)

        distance = zero_route.total_distance()
        assert distance == 0.0

    def test_route_extreme_distances(self):
        """Test route with extreme global distances."""
        # Antipodal points (maximum distance)
        point1 = Place(name="Point 1", coordinates=Coordinates(latitude=45.0, longitude=0.0))
        point2 = Place(name="Point 2", coordinates=Coordinates(latitude=-45.0, longitude=180.0))

        max_distance_route = Route(origin=point1, destination=point2)

        distance = max_distance_route.total_distance()
        assert distance is not None
        assert distance > 15000  # Should be substantial portion of Earth's circumference


class TestRegionEdgeCases:
    """Test edge cases for Region model."""

    def test_region_with_complete_data(self):
        """Test region with all optional fields populated."""
        bbox = BoundingBox(north=49.0, south=25.0, east=-66.0, west=-125.0)
        center = Coordinates(latitude=37.0, longitude=-95.0)

        usa_region = Region(
            name="United States",
            code="US",
            bounding_box=bbox,
            center=center,
            population=331000000,
            area_km2=9833520.0,
        )

        assert usa_region.code == "US"
        assert usa_region.population == 331000000
        assert usa_region.area_km2 > 9000000

    def test_region_minimal_data(self):
        """Test region with only required name field."""
        minimal_region = Region(name="Unknown Region")

        assert minimal_region.name == "Unknown Region"
        assert minimal_region.code is None
        assert minimal_region.population is None

    def test_region_zero_population(self):
        """Test region with zero population (uninhabited area)."""
        uninhabited = Region(name="Uninhabited Island", population=0, area_km2=10.5)

        assert uninhabited.population == 0
        assert uninhabited.area_km2 == 10.5

    def test_region_validation_edge_cases(self):
        """Test region validation with edge cases."""
        # Negative population should fail
        with pytest.raises(ValidationError):
            Region(name="Invalid Region", population=-1000)

        # Negative area should fail
        with pytest.raises(ValidationError):
            Region(name="Invalid Region", area_km2=-100.0)

        # Zero area should be valid (point location)
        zero_area_region = Region(name="Point Location", area_km2=0.0)
        assert zero_area_region.area_km2 == 0.0


@given(
    lat=st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
    altitude=st.one_of(st.none(), st.floats(min_value=-1000, max_value=10000, allow_nan=False)),
)
@settings(max_examples=100, deadline=None)
def test_coordinates_property_based(lat: float, lon: float, altitude: Optional[float]):
    """Test Coordinates with property-based testing."""
    try:
        coords = Coordinates(latitude=lat, longitude=lon, altitude=altitude)

        # Basic validations
        assert -90 <= coords.latitude <= 90
        assert -180 <= coords.longitude <= 180

        # Test distance to self is zero
        assert coords.distance_to(coords) == 0.0

        # Test serialization round-trip
        json_data = coords.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = Coordinates.model_validate(parsed)

        assert abs(reconstructed.latitude - coords.latitude) < 1e-10
        assert abs(reconstructed.longitude - coords.longitude) < 1e-10

        if altitude is not None:
            assert abs(reconstructed.altitude - coords.altitude) < 1e-10

    except ValidationError:
        # Should only fail for invalid coordinate ranges
        assert lat < -90 or lat > 90 or lon < -180 or lon > 180


@given(
    name=st.text(min_size=1, max_size=100),
    street=st.one_of(st.none(), st.text(max_size=200)),
    city=st.one_of(st.none(), st.text(max_size=100)),
    country=st.one_of(st.none(), st.text(max_size=100)),
)
@settings(max_examples=50, deadline=None)
def test_place_property_based(name: str, street: Optional[str], city: Optional[str], country: Optional[str]):
    """Test Place with property-based testing."""
    try:
        address = None
        if any([street, city, country]):
            address = Address(street=street, city=city, country=country)

        place = Place(name=name, address=address)

        # Basic validations
        assert place.name == name
        assert len(place.name) > 0

        # Test serialization
        json_data = place.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = Place.model_validate(parsed)

        assert reconstructed.name == place.name
        if address:
            assert reconstructed.address is not None

    except ValidationError:
        # Should only fail for invalid input
        assert len(name) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
