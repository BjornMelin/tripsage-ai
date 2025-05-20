"""Tests for SearchParameters model."""

from datetime import datetime

from tripsage.models.db.search_parameters import SearchParameters


def test_search_parameters_creation(sample_search_parameters_dict):
    """Test creating a SearchParameters model with valid data."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    assert search_params.id == 1
    assert search_params.trip_id == 1
    assert search_params.parameter_json["type"] == "flight"
    assert search_params.parameter_json["origin"] == "LAX"
    assert search_params.parameter_json["destination"] == "NRT"


def test_search_parameters_optional_fields():
    """Test creating a SearchParameters model with minimal required fields."""
    now = datetime.now()
    minimal_search_params = SearchParameters(
        trip_id=1,
        timestamp=now,
        parameter_json={"type": "accommodation", "location": "Tokyo, Japan"},
    )

    assert minimal_search_params.trip_id == 1
    assert minimal_search_params.id is None
    assert minimal_search_params.timestamp == now
    assert minimal_search_params.parameter_json["type"] == "accommodation"


def test_is_flight_search(sample_search_parameters_dict):
    """Test the is_flight_search property."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    assert search_params.is_flight_search is True

    # Change to accommodation search
    search_params.parameter_json["type"] = "accommodation"
    assert search_params.is_flight_search is False


def test_is_accommodation_search(sample_search_parameters_dict):
    """Test the is_accommodation_search property."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    assert search_params.is_accommodation_search is False

    # Change to accommodation search
    search_params.parameter_json["type"] = "accommodation"
    assert search_params.is_accommodation_search is True


def test_is_activity_search(sample_search_parameters_dict):
    """Test the is_activity_search property."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    assert search_params.is_activity_search is False

    # Change to activity search
    search_params.parameter_json["type"] = "activity"
    assert search_params.is_activity_search is True


def test_is_transportation_search(sample_search_parameters_dict):
    """Test the is_transportation_search property."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    assert search_params.is_transportation_search is False

    # Change to transportation search
    search_params.parameter_json["type"] = "transportation"
    assert search_params.is_transportation_search is True


def test_search_summary(sample_search_parameters_dict):
    """Test the search_summary property for flight search."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    expected_summary = "Flight from LAX to NRT (Economy, 2 adults, 0 children)"
    assert search_params.search_summary == expected_summary


def test_search_summary_accommodation():
    """Test the search_summary property for accommodation search."""
    now = datetime.now()
    search_params = SearchParameters(
        trip_id=1,
        timestamp=now,
        parameter_json={
            "type": "accommodation",
            "location": "Tokyo, Japan",
            "check_in": "2023-10-15",
            "check_out": "2023-10-22",
            "adults": 2,
            "accommodation_type": "hotel",
        },
    )
    expected_summary = "Hotel in Tokyo, Japan (2023-10-15 to 2023-10-22, 2 adults)"
    assert search_params.search_summary == expected_summary


def test_search_summary_activity():
    """Test the search_summary property for activity search."""
    now = datetime.now()
    search_params = SearchParameters(
        trip_id=1,
        timestamp=now,
        parameter_json={
            "type": "activity",
            "location": "Tokyo, Japan",
            "date": "2023-10-16",
            "activity_type": "sightseeing",
        },
    )
    expected_summary = "Sightseeing activity in Tokyo, Japan (2023-10-16)"
    assert search_params.search_summary == expected_summary


def test_search_summary_transportation():
    """Test the search_summary property for transportation search."""
    now = datetime.now()
    search_params = SearchParameters(
        trip_id=1,
        timestamp=now,
        parameter_json={
            "type": "transportation",
            "origin": "Tokyo Station",
            "destination": "Kyoto Station",
            "date": "2023-10-16",
            "transportation_type": "train",
        },
    )
    expected_summary = "Train from Tokyo Station to Kyoto Station (2023-10-16)"
    assert search_params.search_summary == expected_summary


def test_search_summary_unknown_type():
    """Test the search_summary property for unknown search type."""
    now = datetime.now()
    search_params = SearchParameters(
        trip_id=1,
        timestamp=now,
        parameter_json={"type": "unknown", "query": "something"},
    )
    expected_summary = (
        "Search for unknown with parameters: {'type': 'unknown', 'query': 'something'}"
    )
    assert search_params.search_summary == expected_summary


def test_model_dump(sample_search_parameters_dict):
    """Test model_dump method."""
    search_params = SearchParameters(**sample_search_parameters_dict)
    params_dict = search_params.model_dump()

    assert params_dict["trip_id"] == 1
    assert params_dict["parameter_json"]["type"] == "flight"
    assert params_dict["parameter_json"]["origin"] == "LAX"
    assert params_dict["parameter_json"]["destination"] == "NRT"
