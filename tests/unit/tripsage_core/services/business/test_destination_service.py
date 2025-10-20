"""Comprehensive tests for DestinationService.

This module provides full test coverage for destination management operations
including search, discovery, weather integration, and travel advisory features.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
    CoreServiceError as ServiceError,
)
from tripsage_core.services.business.destination_service import (
    ClimateType,
    Destination,
    DestinationCategory,
    DestinationImage,
    DestinationSearchRequest,
    DestinationSearchResponse,
    DestinationService,
    DestinationWeather,
    PointOfInterest,
    SafetyLevel,
    get_destination_service,
)


class TestDestinationService:
    """Test suite for DestinationService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        return AsyncMock()

    @pytest.fixture
    def mock_external_api_service(self):
        """Mock external API service."""
        return AsyncMock()

    @pytest.fixture
    def destination_service(self, mock_database_service, mock_external_api_service):
        """Create DestinationService instance with mocked dependencies."""
        return DestinationService(
            database_service=mock_database_service,
            external_api_service=mock_external_api_service,
        )

    @pytest.fixture
    def sample_destination_search_request(self):
        """Sample destination search request."""
        return DestinationSearchRequest(
            query="Paris",
            categories=[DestinationCategory.CITY, DestinationCategory.CULTURAL],
            min_budget=100.00,
            max_budget=500.00,
            travel_dates_start=date.today() + timedelta(days=30),
            travel_dates_end=date.today() + timedelta(days=37),
            travelers=2,
            interests=["history", "art", "food"],
            climate_preferences=[ClimateType.TEMPERATE],
            language_preferences=["en", "fr"],
        )

    @pytest.fixture
    def sample_destination_image(self):
        """Sample destination image."""
        return DestinationImage(
            url="https://example.com/images/eiffel-tower.jpg",
            caption="Eiffel Tower at sunset",
            is_primary=True,
            attribution="Photo by John Doe",
            width=1920,
            height=1080,
        )

    @pytest.fixture
    def sample_poi(self):
        """Sample point of interest."""
        poi_id = str(uuid4())

        return PointOfInterest(
            id=poi_id,
            name="Eiffel Tower",
            category="landmark",
            description="Iconic iron lattice tower built in 1889",
            address="Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
            latitude=48.8584,
            longitude=2.2945,
            rating=4.7,
            review_count=150000,
            price_level=2,
            opening_hours={
                "Monday": "09:30-23:45",
                "Tuesday": "09:30-23:45",
                "Wednesday": "09:30-23:45",
                "Thursday": "09:30-23:45",
                "Friday": "09:30-23:45",
                "Saturday": "09:30-23:45",
                "Sunday": "09:30-23:45",
            },
            images=[],
            website="https://www.toureiffel.paris/",
            phone="+33 892 70 12 39",
            popular_times={
                "Monday": [
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    15,
                    30,
                    45,
                    60,
                    75,
                    85,
                    90,
                    85,
                    75,
                    65,
                    70,
                    80,
                    85,
                    75,
                    55,
                    35,
                    20,
                    0,
                ],
                "Tuesday": [
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    15,
                    30,
                    45,
                    60,
                    75,
                    85,
                    90,
                    85,
                    75,
                    65,
                    70,
                    80,
                    85,
                    75,
                    55,
                    35,
                    20,
                    0,
                ],
            },
        )

    @pytest.fixture
    def sample_destination_weather(self):
        """Sample destination weather."""
        return DestinationWeather(
            season="summer",
            temperature_high_c=25.0,
            temperature_low_c=15.0,
            precipitation_mm=50.0,
            humidity_percent=65.0,
            wind_speed_kmh=15.0,
            uv_index=6,
            conditions="partly_cloudy",
            best_months_to_visit=["May", "June", "September", "October"],
            climate_type=ClimateType.TEMPERATE,
        )

    @pytest.fixture
    def sample_destination_details(
        self, sample_destination_image, sample_poi, sample_destination_weather
    ):
        """Sample destination details."""
        destination_id = str(uuid4())

        return Destination(
            id=destination_id,
            name="Paris",
            country="France",
            region="Île-de-France",
            description=(
                "The City of Light, known for its art, fashion, gastronomy, and culture"
            ),
            categories=[DestinationCategory.CITY, DestinationCategory.CULTURAL],
            latitude=48.8566,
            longitude=2.3522,
            population=2161000,
            timezone="Europe/Paris",
            currency="EUR",
            languages=["French"],
            images=[sample_destination_image],
            points_of_interest=[sample_poi],
            weather=sample_destination_weather,
            safety_level=SafetyLevel.SAFE,
            travel_alerts=[],
            average_daily_cost=150.00,
            best_time_to_visit="April to June, September to October",
            typical_duration_days=4,
            tourist_season_months=[6, 7, 8],
            visa_requirements={"US": "No visa required for stays up to 90 days"},
            transportation_options={
                "metro": "Extensive metro system",
                "bus": "Comprehensive bus network",
                "taxi": "Taxis and ride-sharing available",
                "bike": "Bike-sharing system (Vélib')",
            },
            local_customs=["Greet with 'Bonjour'", "Tip is included in bill"],
            emergency_numbers={"police": "17", "medical": "15", "fire": "18"},
        )

    @pytest.mark.asyncio
    async def test_search_destinations_success(
        self,
        destination_service,
        mock_external_api_service,
        sample_destination_search_request,
        sample_destination_details,
    ):
        """Test successful destination search."""
        user_id = str(uuid4())

        # Mock external API response
        mock_external_api_service.search_destinations.return_value = {
            "results": [sample_destination_details.model_dump()],
            "total": 1,
        }

        result = await destination_service.search_destinations(
            user_id, sample_destination_search_request
        )

        # Assertions
        assert isinstance(result, DestinationSearchResponse)
        assert len(result.destinations) == 1
        assert result.total_results == 1
        assert result.destinations[0].name == "Paris"

        # Verify service calls
        mock_external_api_service.search_destinations.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_destinations_validation_error(self, destination_service):
        """Test destination search with validation errors."""
        # Create invalid search request with end date before start date
        with pytest.raises(ValueError, match="End date must be after start date"):
            DestinationSearchRequest(
                query="Paris",
                travel_dates_start=date.today() + timedelta(days=30),
                travel_dates_end=date.today() + timedelta(days=25),  # Before start
                travelers=2,
            )

    @pytest.mark.asyncio
    async def test_get_destination_details_success(
        self, destination_service, mock_database_service, sample_destination_details
    ):
        """Test successful destination details retrieval."""
        # Mock database response
        mock_database_service.get_destination_by_id.return_value = (
            sample_destination_details.model_dump()
        )

        result = await destination_service.get_destination_details(
            sample_destination_details.id
        )

        assert result is not None
        assert result.id == sample_destination_details.id
        assert result.name == sample_destination_details.name
        assert len(result.points_of_interest) == 1

        mock_database_service.get_destination_by_id.assert_called_once_with(
            sample_destination_details.id
        )

    @pytest.mark.asyncio
    async def test_get_destination_details_not_found(
        self, destination_service, mock_database_service
    ):
        """Test destination details retrieval when not found."""
        destination_id = str(uuid4())

        mock_database_service.get_destination_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Destination not found"):
            await destination_service.get_destination_details(destination_id)

    @pytest.mark.asyncio
    async def test_get_destination_weather_success(
        self, destination_service, mock_external_api_service, sample_destination_weather
    ):
        """Test successful weather information retrieval."""
        destination_id = str(uuid4())

        # Mock weather API response
        mock_external_api_service.get_destination_weather.return_value = (
            sample_destination_weather.model_dump()
        )

        result = await destination_service.get_destination_weather(
            destination_id, date.today() + timedelta(days=7)
        )

        assert result is not None
        assert (
            result.temperature_high_c == sample_destination_weather.temperature_high_c
        )
        assert result.conditions == sample_destination_weather.conditions

        mock_external_api_service.get_destination_weather.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_points_of_interest_success(
        self, destination_service, mock_external_api_service, sample_poi
    ):
        """Test successful POI retrieval."""
        destination_id = str(uuid4())

        # Mock POI API response
        mock_external_api_service.get_points_of_interest.return_value = [
            sample_poi.model_dump()
        ]

        results = await destination_service.get_points_of_interest(
            destination_id, categories=["landmark", "museum"], limit=10
        )

        assert len(results) == 1
        assert results[0].name == sample_poi.name
        assert results[0].category == sample_poi.category

        mock_external_api_service.get_points_of_interest.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_travel_alerts_success(
        self, destination_service, mock_external_api_service
    ):
        """Test successful travel alerts retrieval."""
        destination_id = str(uuid4())

        # Mock travel alerts response
        alerts = [
            {
                "id": str(uuid4()),
                "title": "Public Transport Strike",
                "description": "Metro services disrupted on weekends",
                "severity": "moderate",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=7)).isoformat(),
                "affected_areas": ["Metro Lines 1, 4, 7"],
            }
        ]

        mock_external_api_service.get_travel_alerts.return_value = alerts

        results = await destination_service.get_travel_alerts(destination_id)

        assert len(results) == 1
        assert results[0]["title"] == "Public Transport Strike"
        assert results[0]["severity"] == "moderate"

        mock_external_api_service.get_travel_alerts.assert_called_once_with(
            destination_id
        )

    @pytest.mark.asyncio
    async def test_get_popular_times_success(
        self, destination_service, mock_external_api_service, sample_poi
    ):
        """Test successful popular times retrieval."""
        # Mock popular times response
        mock_external_api_service.get_popular_times.return_value = (
            sample_poi.popular_times
        )

        result = await destination_service.get_popular_times(
            sample_poi.id, day_of_week="Monday"
        )

        assert result is not None
        assert len(result) == 24  # 24 hours
        assert max(result) == 90  # Peak hour

        mock_external_api_service.get_popular_times.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_destinations_success(
        self, destination_service, mock_database_service, sample_destination_details
    ):
        """Test successful destination comparison."""
        destination_ids = [str(uuid4()) for _ in range(3)]

        # Mock destination data
        destinations = []
        for i, dest_id in enumerate(destination_ids):
            dest = sample_destination_details.model_copy()
            dest.id = dest_id
            dest.name = f"City {i + 1}"
            dest.average_daily_cost = 100.00 + (i * 50)
            destinations.append(dest.model_dump())

        # Mock database calls
        mock_database_service.get_destination_by_id.side_effect = destinations

        result = await destination_service.compare_destinations(
            destination_ids, criteria=["cost", "weather", "safety"]
        )

        assert "destinations" in result
        assert "comparison_matrix" in result
        assert len(result["destinations"]) == 3

        # Verify comparison logic
        assert (
            result["comparison_matrix"]["cost"]["best"] == destination_ids[0]
        )  # Lowest cost
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_get_destination_recommendations_success(
        self, destination_service, mock_database_service, mock_external_api_service
    ):
        """Test successful destination recommendations."""
        user_id = str(uuid4())

        # Mock user preferences
        user_preferences = {
            "preferred_categories": [
                DestinationCategory.BEACH,
                DestinationCategory.RELAXATION,
            ],
            "budget_range": {"min": 100, "max": 300},
            "climate_preferences": [ClimateType.TROPICAL],
            "past_destinations": ["Thailand", "Bali"],
        }

        mock_database_service.get_user_travel_preferences.return_value = (
            user_preferences
        )

        # Mock recommendation results
        recommendations = [
            {
                "destination_id": str(uuid4()),
                "name": "Maldives",
                "score": 0.95,
                "reasons": [
                    "Matches climate preference",
                    "Within budget",
                    "Similar to past destinations",
                ],
            }
        ]

        mock_external_api_service.get_destination_recommendations.return_value = (
            recommendations
        )

        result = await destination_service.get_destination_recommendations(
            user_id, limit=5
        )

        assert len(result) == 1
        assert result[0]["name"] == "Maldives"
        assert result[0]["score"] == 0.95

        mock_database_service.get_user_travel_preferences.assert_called_once_with(
            user_id
        )
        mock_external_api_service.get_destination_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_destination_budget_success(
        self, destination_service, mock_database_service
    ):
        """Test successful destination budget calculation."""
        destination_id = str(uuid4())

        # Mock cost data
        cost_data = {
            "accommodation": {"budget": 50, "mid_range": 100, "luxury": 250},
            "food": {"street_food": 10, "restaurant": 30, "fine_dining": 80},
            "transportation": {"public": 5, "taxi": 20, "private": 50},
            "activities": {"free": 0, "paid": 25, "premium": 60},
        }

        mock_database_service.get_destination_costs.return_value = cost_data

        result = await destination_service.calculate_destination_budget(
            destination_id, duration_days=5, travelers=2, budget_level="mid_range"
        )

        assert "total_cost" in result
        assert "daily_average" in result
        assert "breakdown" in result
        assert result["daily_average"] == (100 + 30 + 20 + 25)  # Mid-range costs
        assert (
            result["total_cost"] == result["daily_average"] * 5 * 2
        )  # 5 days, 2 travelers

    @pytest.mark.asyncio
    async def test_get_destination_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_destination_service()
        assert isinstance(service, DestinationService)

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, destination_service, mock_external_api_service
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock external API to raise an exception
        mock_external_api_service.search_destinations.side_effect = Exception(
            "API error"
        )

        search_request = DestinationSearchRequest(query="Paris", travelers=2)

        with pytest.raises(ServiceError, match="Destination search failed"):
            await destination_service.search_destinations(user_id, search_request)

    def test_destination_scoring_logic(self, destination_service):
        """Test destination scoring and ranking logic."""
        # Test internal scoring method if it exists
        destinations = [
            {
                "name": "Paris",
                "average_daily_cost": 150,
                "safety_level": SafetyLevel.SAFE,
                "rating": 4.7,
                "match_score": 0.9,
            },
            {
                "name": "Bangkok",
                "average_daily_cost": 80,
                "safety_level": SafetyLevel.MODERATE,
                "rating": 4.5,
                "match_score": 0.8,
            },
        ]

        # If the service has a scoring method, test it
        if hasattr(destination_service, "_calculate_destination_score"):
            scores = [
                destination_service._calculate_destination_score(dest)
                for dest in destinations
            ]

            assert all(0 <= score <= 1 for score in scores)
            # Paris should have higher score due to better safety and rating
            assert scores[0] > scores[1]
