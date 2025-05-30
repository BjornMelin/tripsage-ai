"""Tests for the module initialization in tripsage.models.db."""

import importlib

from tripsage_core.models.db import (
    Accommodation,
    AccommodationBookingStatus,
    AccommodationType,
    AirlineProvider,
    CancellationPolicy,
    DataSource,
    EntityType,
    Flight,
    FlightBookingStatus,
    OptionType,
    PriceHistory,
    SavedOption,
    SearchParameters,
    Transportation,
    TransportationBookingStatus,
    TransportationType,
    Trip,
    TripComparison,
    TripNote,
    TripStatus,
    TripVisibility,
    # Models
    User,
    # Enums
    UserRole,
)


def test_model_imports():
    """Test that all models can be imported correctly."""
    assert User.__name__ == "User"
    assert Trip.__name__ == "Trip"
    assert Flight.__name__ == "Flight"
    assert Accommodation.__name__ == "Accommodation"
    assert SearchParameters.__name__ == "SearchParameters"
    assert TripNote.__name__ == "TripNote"
    assert PriceHistory.__name__ == "PriceHistory"
    assert SavedOption.__name__ == "SavedOption"
    assert TripComparison.__name__ == "TripComparison"
    assert Transportation.__name__ == "Transportation"


def test_enum_imports():
    """Test that all enums can be imported correctly."""
    assert UserRole.__name__ == "UserRole"
    assert TripStatus.__name__ == "TripStatus"
    assert TripVisibility.__name__ == "TripVisibility"
    assert AirlineProvider.__name__ == "AirlineProvider"
    assert AccommodationBookingStatus.__name__ == "BookingStatus"
    assert FlightBookingStatus.__name__ == "BookingStatus"
    assert TransportationBookingStatus.__name__ == "BookingStatus"
    assert DataSource.__name__ == "DataSource"
    assert AccommodationType.__name__ == "AccommodationType"
    assert CancellationPolicy.__name__ == "CancellationPolicy"
    assert EntityType.__name__ == "EntityType"
    assert OptionType.__name__ == "OptionType"
    assert TransportationType.__name__ == "TransportationType"


def test_model_inheritance():
    """Test that all models inherit from TripSageModel."""
    from tripsage_core.models.base_core_model import TripSageModel

    assert issubclass(User, TripSageModel)
    assert issubclass(Trip, TripSageModel)
    assert issubclass(Flight, TripSageModel)
    assert issubclass(Accommodation, TripSageModel)
    assert issubclass(SearchParameters, TripSageModel)
    assert issubclass(TripNote, TripSageModel)
    assert issubclass(PriceHistory, TripSageModel)
    assert issubclass(SavedOption, TripSageModel)
    assert issubclass(TripComparison, TripSageModel)
    assert issubclass(Transportation, TripSageModel)


def test_no_circular_imports():
    """Test that there are no circular imports."""
    # Re-import the module to check for circular import errors
    importlib.reload(importlib.import_module("tripsage.models.db"))
    # If we get here without errors, the test passes
