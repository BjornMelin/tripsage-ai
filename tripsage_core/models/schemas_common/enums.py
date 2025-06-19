"""
Centralized enumerations for TripSage AI.

This module contains all shared enums used across the TripSage application.
These enums provide a single source of truth for status values, types,
and other categorical data used throughout the system.
"""

from enum import Enum


class BookingStatus(str, Enum):
    """Status of a booking across all booking types (accommodations, flights, etc.)."""

    VIEWED = "viewed"
    SAVED = "saved"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class TripStatus(str, Enum):
    """Status of a trip throughout its lifecycle."""

    PLANNING = "planning"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AccommodationType(str, Enum):
    """Types of accommodations available for booking."""

    # Basic types
    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOSTEL = "hostel"
    RESORT = "resort"
    VILLA = "villa"
    HOUSE = "house"

    # Extended types
    BED_AND_BREAKFAST = "bed_and_breakfast"
    GUEST_HOUSE = "guest_house"
    BOUTIQUE_HOTEL = "boutique_hotel"
    CABIN = "cabin"
    COTTAGE = "cottage"

    # Generic
    OTHER = "other"
    ALL = "all"  # For search filters


class CancellationPolicy(str, Enum):
    """Cancellation policies for bookings."""

    FREE = "free"
    PARTIAL_REFUND = "partial_refund"
    NO_REFUND = "no_refund"
    FLEXIBLE = "flexible"
    MODERATE = "moderate"
    STRICT = "strict"
    UNKNOWN = "unknown"


class UserRole(str, Enum):
    """User roles in the system."""

    USER = "user"
    ADMIN = "admin"


class CabinClass(str, Enum):
    """Flight cabin classes."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class PaymentType(str, Enum):
    """Payment methods and types."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class CurrencyCode(str, Enum):
    """ISO 4217 currency codes for the most common currencies."""

    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan
    SEK = "SEK"  # Swedish Krona
    NZD = "NZD"  # New Zealand Dollar
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    PLN = "PLN"  # Polish Złoty
    CZK = "CZK"  # Czech Koruna
    HUF = "HUF"  # Hungarian Forint
    RUB = "RUB"  # Russian Ruble
    BRL = "BRL"  # Brazilian Real
    INR = "INR"  # Indian Rupee
    KRW = "KRW"  # South Korean Won
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar
    MXN = "MXN"  # Mexican Peso
    ZAR = "ZAR"  # South African Rand
    TRY = "TRY"  # Turkish Lira
    THB = "THB"  # Thai Baht


class PassengerType(str, Enum):
    """Types of passengers for flight bookings."""

    ADULT = "adult"
    CHILD = "child"
    INFANT = "infant"


class FareType(str, Enum):
    """Flight fare types."""

    ECONOMY_BASIC = "economy_basic"
    ECONOMY_STANDARD = "economy_standard"
    ECONOMY_FLEX = "economy_flex"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST_CLASS = "first_class"


class OrderState(str, Enum):
    """Order states for bookings."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class TemperatureUnit(str, Enum):
    """Temperature measurement units."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"


class WindSpeedUnit(str, Enum):
    """Wind speed measurement units."""

    KMH = "kmh"  # kilometers per hour
    MPH = "mph"  # miles per hour
    MS = "ms"  # meters per second
    KNOTS = "knots"


class PressureUnit(str, Enum):
    """Atmospheric pressure measurement units."""

    HPA = "hpa"  # hectopascals
    MBAR = "mbar"  # millibars
    INHG = "inhg"  # inches of mercury
    MMHG = "mmhg"  # millimeters of mercury


class AirQualityIndex(str, Enum):
    """Air quality index levels."""

    GOOD = "good"
    MODERATE = "moderate"
    UNHEALTHY_SENSITIVE = "unhealthy_for_sensitive_groups"
    UNHEALTHY = "unhealthy"
    VERY_UNHEALTHY = "very_unhealthy"
    HAZARDOUS = "hazardous"


class Priority(str, Enum):
    """General priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SearchSortOrder(str, Enum):
    """Sort order for search results."""

    RELEVANCE = "relevance"
    PRICE_LOW_TO_HIGH = "price_asc"
    PRICE_HIGH_TO_LOW = "price_desc"
    RATING = "rating"
    DISTANCE = "distance"
    DURATION = "duration"
    DEPARTURE_TIME = "departure_time"
    ARRIVAL_TIME = "arrival_time"
    NEWEST = "newest"
    OLDEST = "oldest"


class NotificationType(str, Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    BOOKING_CONFIRMATION = "booking_confirmation"
    PRICE_ALERT = "price_alert"
    TRIP_REMINDER = "trip_reminder"
    PAYMENT_REMINDER = "payment_reminder"


class AirlineProvider(str, Enum):
    """Airline providers for flight bookings."""

    AMERICAN = "american"
    DELTA = "delta"
    UNITED = "united"
    SOUTHWEST = "southwest"
    JETBLUE = "jetblue"
    ALASKA = "alaska"
    SPIRIT = "spirit"
    FRONTIER = "frontier"
    LUFTHANSA = "lufthansa"
    AIR_FRANCE = "air_france"
    BRITISH_AIRWAYS = "british_airways"
    JAPAN_AIRLINES = "japan_airlines"
    EMIRATES = "emirates"
    SINGAPORE_AIRLINES = "singapore_airlines"
    OTHER = "other"


class DataSource(str, Enum):
    """Data source providers for travel information."""

    EXPEDIA = "expedia"
    KAYAK = "kayak"
    SKYSCANNER = "skyscanner"
    GOOGLE_FLIGHTS = "google_flights"
    DUFFEL = "duffel"
    AIRLINE_DIRECT = "airline_direct"
    BOOKING_COM = "booking_com"
    AIRBNB = "airbnb"
    GOOGLE_MAPS = "google_maps"
    TRIPADVISOR = "tripadvisor"
    API_DIRECT = "api_direct"
    OTHER = "other"


class TransportationType(str, Enum):
    """Types of transportation methods."""

    CAR_RENTAL = "car_rental"
    PUBLIC_TRANSIT = "public_transit"
    TAXI = "taxi"
    RIDESHARE = "rideshare"
    SHUTTLE = "shuttle"
    FERRY = "ferry"
    TRAIN = "train"
    BUS = "bus"
    BIKE_RENTAL = "bike_rental"
    SCOOTER = "scooter"
    WALKING = "walking"
    OTHER = "other"


class TripType(str, Enum):
    """Enum for trip type values."""

    LEISURE = "leisure"
    BUSINESS = "business"
    FAMILY = "family"
    SOLO = "solo"
    OTHER = "other"


class TripVisibility(str, Enum):
    """Enum for trip visibility values."""

    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"
