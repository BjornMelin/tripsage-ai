"""
Tests for trip response schemas.

This module tests the Pydantic models used for API responses
related to trips sent to the Next.js frontend.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.responses.trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSearchResponse,
    TripSummaryResponse,
)
from tripsage_core.models.schemas_common.enums import TripStatus
from tripsage_core.models.schemas_common.financial import Budget, Price
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import (
    TripDestination,
    TripPreferences,
)


class TestTripResponse:
    """Test TripResponse schema."""

    def test_valid_trip_response(self):
        """Test valid trip response."""
        trip_id = uuid4()
        destinations = [
            TripDestination(
                name="Paris",
                country="France",
                city="Paris",
                coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
                arrival_date=date(2025, 6, 1),
                departure_date=date(2025, 6, 5),
                duration_days=4,
            ),
        ]
        preferences = TripPreferences(
            activities=["sightseeing", "museums"],
            group_size=2,
        )

        data = {
            "id": trip_id,
            "user_id": "user_123",
            "title": "Paris Vacation",
            "description": "A wonderful trip to Paris",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 5),
            "duration_days": 4,
            "destinations": destinations,
            "preferences": preferences,
            "status": TripStatus.PLANNING,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "updated_at": datetime(2025, 1, 16, 9, 45),
        }

        response = TripResponse(**data)
        assert response.id == trip_id
        assert response.title == "Paris Vacation"
        assert len(response.destinations) == 1
        assert response.preferences.group_size == 2

    def test_minimal_trip_response(self):
        """Test trip response with minimal required fields."""
        trip_id = uuid4()
        destinations = [TripDestination(name="Boston")]

        data = {
            "id": trip_id,
            "user_id": "user_456",
            "title": "Weekend Trip",
            "start_date": date(2025, 3, 1),
            "end_date": date(2025, 3, 3),
            "duration_days": 2,
            "destinations": destinations,
            "status": TripStatus.PLANNING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        response = TripResponse(**data)
        assert response.description is None
        assert response.preferences is None
        assert response.itinerary_id is None

    def test_trip_with_itinerary(self):
        """Test trip response with itinerary."""
        trip_id = uuid4()
        itinerary_id = uuid4()
        destinations = [TripDestination(name="Tokyo")]

        data = {
            "id": trip_id,
            "user_id": "user_789",
            "title": "Tokyo Adventure",
            "start_date": date(2025, 4, 1),
            "end_date": date(2025, 4, 10),
            "duration_days": 9,
            "destinations": destinations,
            "itinerary_id": itinerary_id,
            "status": TripStatus.BOOKED,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        response = TripResponse(**data)
        assert response.itinerary_id == itinerary_id
        assert response.status == TripStatus.BOOKED

    def test_required_fields(self):
        """Test that required fields are enforced."""
        base_data = {
            "user_id": "user_123",
            "title": "Test Trip",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 5),
            "duration_days": 4,
            "destinations": [TripDestination(name="Paris")],
            "status": TripStatus.PLANNING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Missing id
        with pytest.raises(ValidationError):
            TripResponse(**base_data)

        # Missing user_id
        with pytest.raises(ValidationError):
            TripResponse(**{**base_data, "id": uuid4()})

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = TripResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["title"] == "Summer Vacation in Europe"
        assert len(example["destinations"]) >= 1


class TestTripListItem:
    """Test TripListItem schema."""

    def test_valid_trip_list_item(self):
        """Test valid trip list item."""
        trip_id = uuid4()
        data = {
            "id": trip_id,
            "title": "European Tour",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "duration_days": 14,
            "destinations": ["Paris", "Rome", "Barcelona"],
            "status": TripStatus.PLANNING,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "thumbnail_url": "/images/trips/europe.jpg",
        }

        item = TripListItem(**data)
        assert item.id == trip_id
        assert len(item.destinations) == 3
        assert item.thumbnail_url == "/images/trips/europe.jpg"

    def test_minimal_trip_list_item(self):
        """Test trip list item with minimal fields."""
        trip_id = uuid4()
        data = {
            "id": trip_id,
            "title": "Day Trip",
            "start_date": date(2025, 3, 1),
            "end_date": date(2025, 3, 1),
            "duration_days": 1,
            "destinations": ["Boston"],
            "status": TripStatus.COMPLETED,
            "created_at": datetime.now(),
        }

        item = TripListItem(**data)
        assert item.thumbnail_url is None
        assert item.duration_days == 1

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing destinations
        with pytest.raises(ValidationError):
            TripListItem(
                id=uuid4(),
                title="Test Trip",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 5),
                duration_days=4,
                status=TripStatus.PLANNING,
                created_at=datetime.now(),
            )

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = TripListItem.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["title"] == "Summer Vacation in Europe"
        assert isinstance(example["destinations"], list)


class TestTripListResponse:
    """Test TripListResponse schema."""

    def test_valid_trip_list_response(self):
        """Test valid trip list response."""
        items = [
            TripListItem(
                id=uuid4(),
                title="Trip 1",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 5),
                duration_days=4,
                destinations=["Paris"],
                status=TripStatus.PLANNING,
                created_at=datetime.now(),
            ),
            TripListItem(
                id=uuid4(),
                title="Trip 2",
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 10),
                duration_days=9,
                destinations=["Tokyo"],
                status=TripStatus.BOOKED,
                created_at=datetime.now(),
            ),
        ]

        data = {
            "items": items,
            "total": 15,
            "skip": 0,
            "limit": 10,
            "has_more": True,
        }

        response = TripListResponse(**data)
        assert len(response.items) == 2
        assert response.total == 15
        assert response.has_more is True

    def test_empty_trip_list_response(self):
        """Test empty trip list response."""
        data = {
            "items": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
            "has_more": False,
        }

        response = TripListResponse(**data)
        assert len(response.items) == 0
        assert response.total == 0
        assert response.has_more is False

    def test_pagination_fields(self):
        """Test pagination field validation."""
        base_data = {
            "items": [],
            "total": 5,
            "skip": 10,
            "limit": 5,
        }

        # No more items available
        response = TripListResponse(**{**base_data, "has_more": False})
        assert response.skip == 10
        assert response.limit == 5

        # More items available
        response = TripListResponse(**{**base_data, "has_more": True})
        assert response.has_more is True

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing items
        with pytest.raises(ValidationError):
            TripListResponse(
                total=10,
                skip=0,
                limit=10,
                has_more=False,
            )

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = TripListResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert isinstance(example["items"], list)
        assert "total" in example


class TestTripSummaryResponse:
    """Test TripSummaryResponse schema."""

    def test_valid_trip_summary_response(self):
        """Test valid trip summary response."""
        trip_id = uuid4()
        budget = Budget(
            total_budget=Price(amount=Decimal("5000.00"), currency="USD"),
            allocated=Price(amount=Decimal("3500.00"), currency="USD"),
        )

        data = {
            "id": trip_id,
            "title": "European Adventure",
            "date_range": "Jun 1-15, 2025",
            "duration_days": 14,
            "destinations": ["Paris", "Rome", "Barcelona"],
            "status": TripStatus.PLANNING,
            "total_budget": Price(amount=Decimal("5000.00"), currency="USD"),
            "estimated_cost": Price(amount=Decimal("4200.00"), currency="USD"),
            "accommodation_summary": "4-star hotels in city centers",
            "transportation_summary": "Economy flights with connections",
            "budget_summary": budget,
            "has_itinerary": True,
            "completion_percentage": 75,
            "next_action": "Book flights",
        }

        response = TripSummaryResponse(**data)
        assert response.id == trip_id
        assert response.completion_percentage == 75
        assert response.next_action == "Book flights"

    def test_minimal_trip_summary_response(self):
        """Test trip summary with minimal fields."""
        trip_id = uuid4()
        data = {
            "id": trip_id,
            "title": "Weekend Trip",
            "date_range": "Mar 1-3, 2025",
            "duration_days": 2,
            "destinations": ["Boston"],
            "status": TripStatus.COMPLETED,
            "has_itinerary": False,
            "completion_percentage": 100,
        }

        response = TripSummaryResponse(**data)
        assert response.accommodation_summary is None
        assert response.transportation_summary is None
        assert response.budget_summary is None
        assert response.next_action is None

    def test_completion_percentage_validation(self):
        """Test completion percentage validation."""
        base_data = {
            "id": uuid4(),
            "title": "Test Trip",
            "date_range": "Jun 1-5, 2025",
            "duration_days": 4,
            "destinations": ["Paris"],
            "status": TripStatus.PLANNING,
            "has_itinerary": False,
        }

        # Valid boundary values
        response = TripSummaryResponse(**{**base_data, "completion_percentage": 0})
        assert response.completion_percentage == 0

        response = TripSummaryResponse(**{**base_data, "completion_percentage": 100})
        assert response.completion_percentage == 100

        # Invalid values
        with pytest.raises(ValidationError):
            TripSummaryResponse(**{**base_data, "completion_percentage": -1})

        with pytest.raises(ValidationError):
            TripSummaryResponse(**{**base_data, "completion_percentage": 101})

    def test_duration_validation(self):
        """Test duration validation from parent class."""
        base_data = {
            "id": uuid4(),
            "title": "Test Trip",
            "date_range": "Jun 1-5, 2025",
            "destinations": ["Paris"],
            "status": TripStatus.PLANNING,
            "has_itinerary": False,
            "completion_percentage": 50,
        }

        # Valid duration
        response = TripSummaryResponse(**{**base_data, "duration_days": 5})
        assert response.duration_days == 5

        # Invalid duration
        with pytest.raises(ValidationError, match="Duration must be at least 1 day"):
            TripSummaryResponse(**{**base_data, "duration_days": 0})

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = TripSummaryResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["title"] == "Summer Vacation in Europe"
        assert "completion_percentage" in example


class TestTripSearchResponse:
    """Test TripSearchResponse schema."""

    def test_valid_trip_search_response(self):
        """Test valid trip search response."""
        trip_list = TripListResponse(
            items=[
                TripListItem(
                    id=uuid4(),
                    title="European Tour",
                    start_date=date(2025, 6, 1),
                    end_date=date(2025, 6, 15),
                    duration_days=14,
                    destinations=["Paris", "Rome"],
                    status=TripStatus.PLANNING,
                    created_at=datetime.now(),
                ),
            ],
            total=1,
            skip=0,
            limit=10,
            has_more=False,
        )

        data = {
            "query": "European vacation",
            "filters_applied": {
                "destination": "Europe",
                "min_duration": 7,
                "status": "planning",
            },
            "results": trip_list,
            "suggestions": ["Mediterranean cruise", "UK Scotland tour"],
        }

        response = TripSearchResponse(**data)
        assert response.query == "European vacation"
        assert response.filters_applied["destination"] == "Europe"
        assert len(response.suggestions) == 2

    def test_empty_search_response(self):
        """Test empty search response."""
        empty_list = TripListResponse(
            items=[],
            total=0,
            skip=0,
            limit=10,
            has_more=False,
        )

        data = {
            "results": empty_list,
        }

        response = TripSearchResponse(**data)
        assert response.query is None
        assert response.filters_applied == {}
        assert response.suggestions is None

    def test_search_with_filters_only(self):
        """Test search response with filters but no query."""
        trip_list = TripListResponse(
            items=[],
            total=0,
            skip=0,
            limit=10,
            has_more=False,
        )

        data = {
            "filters_applied": {
                "start_date_from": "2025-06-01",
                "max_duration": 14,
            },
            "results": trip_list,
        }

        response = TripSearchResponse(**data)
        assert response.query is None
        assert response.filters_applied["max_duration"] == 14

    def test_required_fields(self):
        """Test that results field is required."""
        with pytest.raises(ValidationError):
            TripSearchResponse(
                query="test",
                filters_applied={},
            )

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = TripSearchResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert "query" in example
        assert "results" in example


class TestTripResponseIntegration:
    """Test integration scenarios for trip responses."""

    def test_trip_list_to_detail_flow(self):
        """Test flow from trip list to trip detail."""
        trip_id = uuid4()

        # Trip in list
        list_item = TripListItem(
            id=trip_id,
            title="Paris Vacation",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 5),
            duration_days=4,
            destinations=["Paris"],
            status=TripStatus.PLANNING,
            created_at=datetime.now(),
        )
        assert list_item.id == trip_id

        # Full trip details
        destinations = [
            TripDestination(
                name="Paris",
                country="France",
                coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
            ),
        ]
        trip_detail = TripResponse(
            id=trip_id,
            user_id="user_123",
            title="Paris Vacation",
            description="Extended details about the Paris trip",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 5),
            duration_days=4,
            destinations=destinations,
            status=TripStatus.PLANNING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert trip_detail.id == trip_id
        assert trip_detail.description is not None

    def test_search_to_summary_flow(self):
        """Test flow from search results to trip summary."""
        trip_id = uuid4()

        # Search result
        search_item = TripListItem(
            id=trip_id,
            title="Mediterranean Cruise",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 14),
            duration_days=13,
            destinations=["Barcelona", "Rome", "Athens"],
            status=TripStatus.BOOKED,
            created_at=datetime.now(),
        )

        search_response = TripSearchResponse(
            query="Mediterranean cruise",
            filters_applied={"min_duration": 10},
            results=TripListResponse(
                items=[search_item],
                total=1,
                skip=0,
                limit=10,
                has_more=False,
            ),
        )
        assert len(search_response.results.items) == 1

        # Trip summary
        budget = Budget(
            total_budget=Price(amount=Decimal("8000.00"), currency="USD"),
            spent=Price(amount=Decimal("6500.00"), currency="USD"),
        )
        summary = TripSummaryResponse(
            id=trip_id,
            title="Mediterranean Cruise",
            date_range="Aug 1-14, 2025",
            duration_days=13,
            destinations=["Barcelona", "Rome", "Athens"],
            status=TripStatus.BOOKED,
            total_budget=Price(amount=Decimal("8000.00"), currency="USD"),
            budget_summary=budget,
            has_itinerary=True,
            completion_percentage=95,
            next_action="Complete check-in",
        )
        assert summary.id == trip_id
        assert summary.completion_percentage == 95

    def test_trip_status_progression(self):
        """Test trip responses across different statuses."""
        trip_id = uuid4()
        base_data = {
            "id": trip_id,
            "title": "Status Progression Trip",
            "date_range": "Jul 1-10, 2025",
            "duration_days": 9,
            "destinations": ["Tokyo"],
            "has_itinerary": False,
        }

        # Planning stage
        planning_summary = TripSummaryResponse(
            **base_data,
            status=TripStatus.PLANNING,
            completion_percentage=25,
            next_action="Add more destinations",
        )
        assert planning_summary.status == TripStatus.PLANNING

        # Booked stage
        booked_summary = TripSummaryResponse(
            **base_data,
            status=TripStatus.BOOKED,
            completion_percentage=90,
            next_action="Pack bags",
            has_itinerary=True,
        )
        assert booked_summary.status == TripStatus.BOOKED
        assert booked_summary.has_itinerary is True

        # Completed stage
        completed_summary = TripSummaryResponse(
            **base_data,
            status=TripStatus.COMPLETED,
            completion_percentage=100,
            next_action=None,
            has_itinerary=True,
        )
        assert completed_summary.status == TripStatus.COMPLETED
        assert completed_summary.next_action is None

    def test_budget_tracking_across_responses(self):
        """Test budget information consistency across response types."""
        trip_id = uuid4()
        total_budget = Price(amount=Decimal("5000.00"), currency="USD")
        estimated_cost = Price(amount=Decimal("4200.00"), currency="USD")

        budget = Budget(
            total_budget=total_budget,
            allocated=Price(amount=Decimal("3500.00"), currency="USD"),
            spent=Price(amount=Decimal("1000.00"), currency="USD"),
        )

        # Trip detail with budget
        trip_detail = TripResponse(
            id=trip_id,
            user_id="user_123",
            title="Budget Trip",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
            duration_days=9,
            destinations=[TripDestination(name="Paris")],
            preferences=TripPreferences(budget=budget),
            status=TripStatus.PLANNING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert trip_detail.preferences.budget.total_budget.amount == Decimal("5000.00")

        # Trip summary with budget
        summary = TripSummaryResponse(
            id=trip_id,
            title="Budget Trip",
            date_range="Jun 1-10, 2025",
            duration_days=9,
            destinations=["Paris"],
            status=TripStatus.PLANNING,
            total_budget=total_budget,
            estimated_cost=estimated_cost,
            budget_summary=budget,
            has_itinerary=False,
            completion_percentage=60,
        )
        assert summary.budget_summary.total_budget.amount == Decimal("5000.00")
        assert summary.estimated_cost.amount == Decimal("4200.00")
