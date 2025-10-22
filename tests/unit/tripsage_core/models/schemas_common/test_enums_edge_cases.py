"""Edge case tests for enums.

This module provides edge case testing for all enumeration
types used across the TripSage application, including value validation,
case sensitivity, serialization, and integration with Pydantic models.
"""

import json

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import BaseModel, ValidationError

from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    AirlineProvider,
    AirQualityIndex,
    BookingStatus,
    CabinClass,
    CancellationPolicy,
    CurrencyCode,
    DataSource,
    FareType,
    NotificationType,
    OrderState,
    PassengerType,
    PaymentType,
    PressureUnit,
    Priority,
    SearchSortOrder,
    TemperatureUnit,
    TransportationType,
    TripStatus,
    TripType,
    TripVisibility,
    UserRole,
    WindSpeedUnit,
)


class TestEnumValidationEdgeCases:
    """Test edge cases for enum validation and usage."""

    def test_enum_case_sensitivity(self):
        """Test enum case sensitivity across all enums."""
        # Test that enum values are case sensitive by default
        assert TripStatus.PLANNING.value == "planning"
        assert TripStatus.PLANNING.value != "PLANNING"
        assert TripStatus.PLANNING.value != "Planning"

        # Test with Pydantic model
        class TestModel(BaseModel):
            status: TripStatus

        # Valid case
        model = TestModel(status="planning")
        assert model.status == TripStatus.PLANNING

        # Invalid case - should fail with strict enum validation
        with pytest.raises(ValidationError):
            TestModel(status="PLANNING")

        with pytest.raises(ValidationError):
            TestModel(status="Planning")

    def test_currency_code_completeness(self):
        """Test that currency codes cover major world currencies."""
        expected_major_currencies = {
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CAD",
            "AUD",
            "CHF",
            "CNY",
            "SEK",
            "NZD",
            "NOK",
            "DKK",
            "INR",
            "BRL",
            "KRW",
            "SGD",
            "HKD",
            "MXN",
            "ZAR",
            "TRY",
            "THB",
        }

        available_currencies = {currency.value for currency in CurrencyCode}

        # Verify all expected major currencies are available
        missing_currencies = expected_major_currencies - available_currencies
        assert not missing_currencies, f"Missing currencies: {missing_currencies}"

        # Test that all currency codes are 3 characters
        for currency in CurrencyCode:
            assert len(currency.value) == 3
            assert currency.value.isupper()
            assert currency.value.isalpha()

    def test_accommodation_type_coverage(self):
        """Test accommodation type enum coverage."""
        # Test that we have basic accommodation types
        basic_types = {
            AccommodationType.HOTEL,
            AccommodationType.APARTMENT,
            AccommodationType.HOSTEL,
            AccommodationType.RESORT,
        }

        for acc_type in basic_types:
            assert isinstance(acc_type.value, str)
            assert len(acc_type.value) > 0

        # Test special values
        assert AccommodationType.ALL.value == "all"
        assert AccommodationType.OTHER.value == "other"

    def test_enum_serialization_deserialization(self):
        """Test enum serialization and deserialization."""

        class ComplexModel(BaseModel):
            trip_status: TripStatus
            accommodation: AccommodationType
            currency: CurrencyCode
            priority: Priority
            user_role: UserRole

        # Create model with various enum values
        original = ComplexModel(
            trip_status=TripStatus.PLANNING,
            accommodation=AccommodationType.HOTEL,
            currency=CurrencyCode.USD,
            priority=Priority.HIGH,
            user_role=UserRole.USER,
        )

        # Test JSON serialization
        json_data = original.model_dump_json()
        parsed_json = json.loads(json_data)

        # Verify enum values are serialized as strings
        assert parsed_json["trip_status"] == "planning"
        assert parsed_json["accommodation"] == "hotel"
        assert parsed_json["currency"] == "USD"
        assert parsed_json["priority"] == "high"
        assert parsed_json["user_role"] == "user"

        # Test deserialization
        reconstructed = ComplexModel.model_validate(parsed_json)
        assert reconstructed.trip_status == TripStatus.PLANNING
        assert reconstructed.accommodation == AccommodationType.HOTEL
        assert reconstructed.currency == CurrencyCode.USD
        assert reconstructed.priority == Priority.HIGH
        assert reconstructed.user_role == UserRole.USER

    def test_enum_invalid_values(self):
        """Test enum validation with invalid values."""

        class TestModel(BaseModel):
            status: TripStatus
            currency: CurrencyCode

        # Test with completely invalid values
        invalid_cases = [
            {"status": "invalid_status", "currency": "USD"},
            {"status": "planning", "currency": "INVALID"},
            {"status": "", "currency": "USD"},
            {"status": "planning", "currency": ""},
            {"status": None, "currency": "USD"},
            {"status": "planning", "currency": None},
            {"status": 123, "currency": "USD"},
            {"status": "planning", "currency": 123},
        ]

        for invalid_data in invalid_cases:
            with pytest.raises(ValidationError):
                TestModel(**invalid_data)

    def test_booking_status_workflow(self):
        """Test booking status enum represents a logical workflow."""
        # Test that booking statuses represent a logical progression
        workflow_order = [
            BookingStatus.VIEWED,
            BookingStatus.SAVED,
            BookingStatus.BOOKED,
            BookingStatus.CANCELLED,
        ]

        # Verify all statuses exist and have string values
        for status in workflow_order:
            assert isinstance(status.value, str)
            assert len(status.value) > 0

        # Test that cancelled is a valid end state
        assert BookingStatus.CANCELLED.value == "cancelled"

    def test_trip_status_lifecycle(self):
        """Test trip status enum represents complete lifecycle."""
        lifecycle_statuses = [
            TripStatus.PLANNING,
            TripStatus.BOOKED,
            TripStatus.IN_PROGRESS,
            TripStatus.COMPLETED,
            TripStatus.CANCELLED,
        ]

        # Verify all lifecycle statuses exist
        for status in lifecycle_statuses:
            assert isinstance(status.value, str)

        # Test logical transitions (business logic test)
        planning_trip = TripStatus.PLANNING
        assert planning_trip.value == "planning"

        # Cancelled should be available from any state
        assert TripStatus.CANCELLED.value == "cancelled"

    def test_payment_type_coverage(self):
        """Test payment type enum covers common payment methods."""
        expected_payment_methods = {
            "credit_card",
            "debit_card",
            "paypal",
            "bank_transfer",
            "crypto",
            "cash",
            "other",
        }

        available_methods = {method.value for method in PaymentType}

        # Verify all expected payment methods are covered
        missing_methods = expected_payment_methods - available_methods
        assert not missing_methods, f"Missing payment methods: {missing_methods}"

    def test_airline_provider_coverage(self):
        """Test airline provider enum covers major airlines."""
        # Test that major airlines are represented
        major_airlines = {
            AirlineProvider.AMERICAN,
            AirlineProvider.DELTA,
            AirlineProvider.UNITED,
            AirlineProvider.LUFTHANSA,
            AirlineProvider.BRITISH_AIRWAYS,
            AirlineProvider.EMIRATES,
        }

        for airline in major_airlines:
            assert isinstance(airline.value, str)
            assert len(airline.value) > 0

        # Test that OTHER is available for unknown airlines
        assert AirlineProvider.OTHER.value == "other"

    def test_data_source_coverage(self):
        """Test data source enum covers major travel platforms."""
        expected_sources = {
            "expedia",
            "kayak",
            "skyscanner",
            "google_flights",
            "duffel",
            "booking_com",
            "airbnb",
            "tripadvisor",
        }

        available_sources = {source.value for source in DataSource}

        # Verify major travel platforms are covered
        for source in expected_sources:
            assert source in available_sources

        # Test that OTHER and API_DIRECT are available
        assert DataSource.OTHER.value == "other"
        assert DataSource.API_DIRECT.value == "api_direct"

    def test_measurement_unit_enums(self):
        """Test measurement unit enums for consistency."""
        # Test temperature units
        temp_units = [
            TemperatureUnit.CELSIUS,
            TemperatureUnit.FAHRENHEIT,
            TemperatureUnit.KELVIN,
        ]
        for unit in temp_units:
            assert isinstance(unit.value, str)
            assert len(unit.value) > 0

        # Test wind speed units
        wind_units = [
            WindSpeedUnit.KMH,
            WindSpeedUnit.MPH,
            WindSpeedUnit.MS,
            WindSpeedUnit.KNOTS,
        ]
        for unit in wind_units:
            assert isinstance(unit.value, str)
            assert len(unit.value) > 0

        # Test pressure units
        pressure_units = [
            PressureUnit.HPA,
            PressureUnit.MBAR,
            PressureUnit.INHG,
            PressureUnit.MMHG,
        ]
        for unit in pressure_units:
            assert isinstance(unit.value, str)
            assert len(unit.value) > 0

    def test_air_quality_index_levels(self):
        """Test air quality index enum covers standard AQI levels."""
        expected_levels = [
            AirQualityIndex.GOOD,
            AirQualityIndex.MODERATE,
            AirQualityIndex.UNHEALTHY_SENSITIVE,
            AirQualityIndex.UNHEALTHY,
            AirQualityIndex.VERY_UNHEALTHY,
            AirQualityIndex.HAZARDOUS,
        ]

        # Verify all standard AQI levels are present
        for level in expected_levels:
            assert isinstance(level.value, str)
            assert len(level.value) > 0

        # Test that values make sense
        assert AirQualityIndex.GOOD.value == "good"
        assert AirQualityIndex.HAZARDOUS.value == "hazardous"

    def test_search_sort_order_options(self):
        """Test search sort order enum covers common sorting needs."""
        sort_options = [
            SearchSortOrder.RELEVANCE,
            SearchSortOrder.PRICE_LOW_TO_HIGH,
            SearchSortOrder.PRICE_HIGH_TO_LOW,
            SearchSortOrder.RATING,
            SearchSortOrder.DISTANCE,
            SearchSortOrder.DURATION,
        ]

        for option in sort_options:
            assert isinstance(option.value, str)
            assert len(option.value) > 0

        # Test specific values
        assert SearchSortOrder.PRICE_LOW_TO_HIGH.value == "price_asc"
        assert SearchSortOrder.PRICE_HIGH_TO_LOW.value == "price_desc"

    def test_notification_type_coverage(self):
        """Test notification type enum covers common notification scenarios."""
        basic_types = [
            NotificationType.INFO,
            NotificationType.SUCCESS,
            NotificationType.WARNING,
            NotificationType.ERROR,
        ]

        travel_specific_types = [
            NotificationType.BOOKING_CONFIRMATION,
            NotificationType.PRICE_ALERT,
            NotificationType.TRIP_REMINDER,
            NotificationType.PAYMENT_REMINDER,
        ]

        all_types = basic_types + travel_specific_types
        for notification_type in all_types:
            assert isinstance(notification_type.value, str)
            assert len(notification_type.value) > 0

    def test_cabin_class_hierarchy(self):
        """Test cabin class enum represents airline class hierarchy."""
        classes = [
            CabinClass.ECONOMY,
            CabinClass.PREMIUM_ECONOMY,
            CabinClass.BUSINESS,
            CabinClass.FIRST,
        ]

        for cabin_class in classes:
            assert isinstance(cabin_class.value, str)
            assert len(cabin_class.value) > 0

        # Test specific values
        assert CabinClass.ECONOMY.value == "economy"
        assert CabinClass.FIRST.value == "first"

    def test_fare_type_compatibility_with_cabin_class(self):
        """Test fare type enum compatibility with cabin classes."""
        economy_fares = [
            FareType.ECONOMY_BASIC,
            FareType.ECONOMY_STANDARD,
            FareType.ECONOMY_FLEX,
        ]

        premium_fares = [
            FareType.PREMIUM_ECONOMY,
            FareType.BUSINESS,
            FareType.FIRST_CLASS,
        ]

        all_fares = economy_fares + premium_fares
        for fare in all_fares:
            assert isinstance(fare.value, str)
            assert len(fare.value) > 0

    def test_cancellation_policy_range(self):
        """Test cancellation policy enum covers policy spectrum."""
        policies = [
            CancellationPolicy.FREE,
            CancellationPolicy.FLEXIBLE,
            CancellationPolicy.MODERATE,
            CancellationPolicy.STRICT,
            CancellationPolicy.NO_REFUND,
        ]

        for policy in policies:
            assert isinstance(policy.value, str)
            assert len(policy.value) > 0

        # Test that UNKNOWN is available
        assert CancellationPolicy.UNKNOWN.value == "unknown"

    def test_order_state_workflow(self):
        """Test order state enum represents order processing workflow."""
        workflow_states = [
            OrderState.PENDING,
            OrderState.CONFIRMED,
            OrderState.PAID,
            OrderState.CANCELLED,
            OrderState.REFUNDED,
            OrderState.EXPIRED,
        ]

        for state in workflow_states:
            assert isinstance(state.value, str)
            assert len(state.value) > 0

        # Test logical end states
        end_states = [
            OrderState.PAID,
            OrderState.CANCELLED,
            OrderState.REFUNDED,
            OrderState.EXPIRED,
        ]

        for state in end_states:
            assert isinstance(state.value, str)

    def test_transportation_type_coverage(self):
        """Test transportation type enum covers various transport modes."""
        land_transport = [
            TransportationType.CAR_RENTAL,
            TransportationType.PUBLIC_TRANSIT,
            TransportationType.TAXI,
            TransportationType.RIDESHARE,
            TransportationType.BUS,
            TransportationType.TRAIN,
        ]

        water_transport = [
            TransportationType.FERRY,
        ]

        personal_transport = [
            TransportationType.BIKE_RENTAL,
            TransportationType.SCOOTER,
            TransportationType.WALKING,
        ]

        all_transport = land_transport + water_transport + personal_transport
        for transport in all_transport:
            assert isinstance(transport.value, str)
            assert len(transport.value) > 0

        # Test that OTHER is available
        assert TransportationType.OTHER.value == "other"

    def test_passenger_type_airline_compliance(self):
        """Test passenger type enum matches airline industry standards."""
        standard_types = [
            PassengerType.ADULT,
            PassengerType.CHILD,
            PassengerType.INFANT,
        ]

        for passenger_type in standard_types:
            assert isinstance(passenger_type.value, str)
            assert len(passenger_type.value) > 0

        # Test specific values match industry standards
        assert PassengerType.ADULT.value == "adult"
        assert PassengerType.CHILD.value == "child"
        assert PassengerType.INFANT.value == "infant"

    def test_trip_visibility_privacy_levels(self):
        """Test trip visibility enum covers privacy requirements."""
        visibility_levels = [
            TripVisibility.PRIVATE,
            TripVisibility.PUBLIC,
            TripVisibility.SHARED,
        ]

        for level in visibility_levels:
            assert isinstance(level.value, str)
            assert len(level.value) > 0

        # Test specific values
        assert TripVisibility.PRIVATE.value == "private"
        assert TripVisibility.PUBLIC.value == "public"
        assert TripVisibility.SHARED.value == "shared"

    def test_trip_type_categories(self):
        """Test trip type enum covers common travel purposes."""
        trip_categories = [
            TripType.LEISURE,
            TripType.BUSINESS,
            TripType.FAMILY,
            TripType.SOLO,
            TripType.OTHER,
        ]

        for category in trip_categories:
            assert isinstance(category.value, str)
            assert len(category.value) > 0

        # Test that OTHER is available for edge cases
        assert TripType.OTHER.value == "other"

    def test_user_role_permission_model(self):
        """Test user role enum supports basic permission model."""
        roles = [
            UserRole.USER,
            UserRole.ADMIN,
        ]

        for role in roles:
            assert isinstance(role.value, str)
            assert len(role.value) > 0

        # Test specific values
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"

    def test_priority_level_ordering(self):
        """Test priority enum represents logical priority ordering."""
        priorities = [
            Priority.LOW,
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.URGENT,
        ]

        for priority in priorities:
            assert isinstance(priority.value, str)
            assert len(priority.value) > 0

        # Test that values represent increasing priority
        assert Priority.LOW.value == "low"
        assert Priority.URGENT.value == "urgent"

    @given(
        enum_class=st.sampled_from(
            [
                TripStatus,
                AccommodationType,
                CurrencyCode,
                PaymentType,
                BookingStatus,
                CabinClass,
                Priority,
                UserRole,
            ]
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_enum_properties_consistency(self, enum_class):
        """Test that all enum values are consistent across different enum types."""
        for enum_value in enum_class:
            # All enum values should be strings
            assert isinstance(enum_value.value, str)

            # All enum values should be non-empty
            assert len(enum_value.value) > 0

            # All enum values should be lowercase or have consistent casing
            value = enum_value.value
            assert value == value.lower() or value == value.upper()

            # No enum values should contain spaces (use underscores instead)
            assert " " not in value

    def test_enum_model_integration_complex(self):
        """Test complex model with multiple enum fields."""

        class TravelBookingModel(BaseModel):
            trip_status: TripStatus
            accommodation_type: AccommodationType
            booking_status: BookingStatus
            payment_type: PaymentType
            currency: CurrencyCode
            cabin_class: CabinClass
            passenger_type: PassengerType
            cancellation_policy: CancellationPolicy
            priority: Priority
            user_role: UserRole

        # Test with valid data
        valid_booking = TravelBookingModel(
            trip_status=TripStatus.PLANNING,
            accommodation_type=AccommodationType.HOTEL,
            booking_status=BookingStatus.SAVED,
            payment_type=PaymentType.CREDIT_CARD,
            currency=CurrencyCode.USD,
            cabin_class=CabinClass.ECONOMY,
            passenger_type=PassengerType.ADULT,
            cancellation_policy=CancellationPolicy.FLEXIBLE,
            priority=Priority.MEDIUM,
            user_role=UserRole.USER,
        )

        # Test serialization
        json_data = valid_booking.model_dump_json()
        parsed = json.loads(json_data)

        # Test deserialization
        reconstructed = TravelBookingModel.model_validate(parsed)

        # Verify all fields are preserved
        assert reconstructed.trip_status == TripStatus.PLANNING
        assert reconstructed.accommodation_type == AccommodationType.HOTEL
        assert reconstructed.booking_status == BookingStatus.SAVED
        assert reconstructed.payment_type == PaymentType.CREDIT_CARD
        assert reconstructed.currency == CurrencyCode.USD
        assert reconstructed.cabin_class == CabinClass.ECONOMY
        assert reconstructed.passenger_type == PassengerType.ADULT
        assert reconstructed.cancellation_policy == CancellationPolicy.FLEXIBLE
        assert reconstructed.priority == Priority.MEDIUM
        assert reconstructed.user_role == UserRole.USER


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
