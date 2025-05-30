"""
Integration tests for Google Maps Location Service.

This module tests the LocationService integration with the Google Maps API,
covering all major location operations and error handling scenarios.
"""

import pytest

from tripsage.services.core.location_service import (
    LocationServiceError,
    get_location_service,
)


class TestLocationServiceIntegration:
    """Integration tests for Google Maps LocationService operations."""

    @pytest.fixture
    def location_service(self):
        """Get location service instance."""
        return get_location_service()

    @pytest.mark.asyncio
    async def test_geocode_success(self, location_service):
        """Test successful geocoding of a well-known address."""
        test_address = "1600 Amphitheatre Parkway, Mountain View, CA"

        result = await location_service.geocode(test_address)

        assert isinstance(result, list)
        assert len(result) > 0

        # Verify structure of first result
        first_result = result[0]
        assert "formatted_address" in first_result
        assert "geometry" in first_result
        assert "location" in first_result["geometry"]
        assert "lat" in first_result["geometry"]["location"]
        assert "lng" in first_result["geometry"]["location"]

    @pytest.mark.asyncio
    async def test_reverse_geocode_success(self, location_service):
        """Test successful reverse geocoding of Google headquarters coordinates."""
        # Google headquarters coordinates
        lat, lng = 37.4224764, -122.0842499

        result = await location_service.reverse_geocode(lat, lng)

        assert isinstance(result, list)
        assert len(result) > 0

        # Verify structure
        first_result = result[0]
        assert "formatted_address" in first_result
        assert "address_components" in first_result

    @pytest.mark.asyncio
    async def test_search_places_success(self, location_service):
        """Test successful place search."""
        query = "restaurants near Google headquarters"
        location = (37.4224764, -122.0842499)  # Google HQ
        radius = 5000  # 5km

        result = await location_service.search_places(query, location, radius)

        assert isinstance(result, dict)
        assert "results" in result
        assert len(result["results"]) > 0

        # Verify structure of first place
        first_place = result["results"][0]
        assert "name" in first_place
        assert "place_id" in first_place
        assert "geometry" in first_place

    @pytest.mark.asyncio
    async def test_get_directions_success(self, location_service):
        """Test successful directions between two locations."""
        origin = "Google headquarters, Mountain View, CA"
        destination = "Apple Park, Cupertino, CA"

        result = await location_service.get_directions(origin, destination)

        assert isinstance(result, list)
        assert len(result) > 0

        # Verify route structure
        first_route = result[0]
        assert "legs" in first_route
        assert "overview_polyline" in first_route
        assert len(first_route["legs"]) > 0

    @pytest.mark.asyncio
    async def test_distance_matrix_success(self, location_service):
        """Test successful distance matrix calculation."""
        origins = ["Google headquarters, Mountain View, CA"]
        destinations = ["Apple Park, Cupertino, CA", "San Francisco, CA"]

        result = await location_service.distance_matrix(origins, destinations)

        assert isinstance(result, dict)
        assert "rows" in result
        assert len(result["rows"]) == 1  # One origin
        assert len(result["rows"][0]["elements"]) == 2  # Two destinations

        # Verify element structure
        element = result["rows"][0]["elements"][0]
        assert "status" in element
        if element["status"] == "OK":
            assert "distance" in element
            assert "duration" in element

    @pytest.mark.asyncio
    async def test_get_elevation_success(self, location_service):
        """Test successful elevation data retrieval."""
        locations = [
            (37.4224764, -122.0842499),  # Google HQ
            (37.7749, -122.4194),  # San Francisco
        ]

        result = await location_service.get_elevation(locations)

        assert isinstance(result, list)
        assert len(result) == 2

        # Verify elevation structure
        for elevation_data in result:
            assert "elevation" in elevation_data
            assert "location" in elevation_data
            assert isinstance(elevation_data["elevation"], (int, float))

    @pytest.mark.asyncio
    async def test_get_timezone_success(self, location_service):
        """Test successful timezone data retrieval."""
        location = (37.4224764, -122.0842499)  # Google HQ

        result = await location_service.get_timezone(location)

        assert isinstance(result, dict)
        assert "timeZoneId" in result
        assert "timeZoneName" in result
        assert "status" in result
        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_geocode_invalid_address(self, location_service):
        """Test geocoding with invalid address."""
        invalid_address = "This is definitely not a real address 12345 INVALID"

        # Should not raise an exception, but may return empty results
        result = await location_service.geocode(invalid_address)

        # Google Maps may return empty results or approximate matches
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_reverse_geocode_invalid_coordinates(self, location_service):
        """Test reverse geocoding with invalid coordinates."""
        # Invalid coordinates (outside valid range)
        lat, lng = 999.0, 999.0

        with pytest.raises(LocationServiceError):
            await location_service.reverse_geocode(lat, lng)

    @pytest.mark.asyncio
    async def test_search_places_no_results(self, location_service):
        """Test place search that returns no results."""
        query = "extremely specific non-existent business name 12345"
        location = (37.4224764, -122.0842499)
        radius = 100  # Very small radius

        result = await location_service.search_places(query, location, radius)

        assert isinstance(result, dict)
        assert "results" in result
        # May return empty results or no matches

    @pytest.mark.asyncio
    async def test_comprehensive_workflow(self, location_service):
        """Test a comprehensive workflow using multiple location operations."""
        try:
            # 1. Geocode a starting location
            address = "Golden Gate Bridge, San Francisco, CA"
            geocode_result = await location_service.geocode(address)
            assert len(geocode_result) > 0

            start_location = geocode_result[0]["geometry"]["location"]
            start_coords = (start_location["lat"], start_location["lng"])

            # 2. Search for nearby attractions
            search_result = await location_service.search_places(
                "tourist attractions", start_coords, 5000
            )
            assert "results" in search_result

            # 3. Get directions to a place
            await location_service.get_directions(
                "Golden Gate Bridge, San Francisco, CA",
                "Alcatraz Island, San Francisco, CA",
            )

            # All operations should complete without exceptions
            assert True, "Comprehensive workflow completed successfully"

        except Exception as e:
            pytest.fail(f"Comprehensive workflow failed: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, location_service):
        """Test concurrent location operations."""
        import asyncio

        # Define multiple operations to run concurrently
        operations = [
            location_service.geocode("New York, NY"),
            location_service.geocode("Los Angeles, CA"),
            location_service.reverse_geocode(40.7128, -74.0060),  # NYC
            location_service.get_timezone((34.0522, -118.2437)),  # LA
        ]

        # Run operations concurrently
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify all operations completed (successfully or with expected errors)
        assert len(results) == 4
        for result in results:
            # Should not be an unexpected exception
            if isinstance(result, Exception):
                assert isinstance(result, LocationServiceError)
            else:
                assert result is not None
